"""ETF portfolio optimization using Google OR-Tools CP-SAT solver."""

import numpy as np
from typing import List, Dict, Tuple, Optional
from ortools.sat.python import cp_model
import asyncio

from .models import ETFWithDistributions, OptimizationRequest, OptimizationResult, ETFAllocation
from .database import ETFDatabase


class ETFOptimizer:
    """Optimizes ETF portfolios using Google OR-Tools CP-SAT solver."""

    def __init__(self, db: ETFDatabase):
        self.db = db

    async def optimize_portfolio(
        self, 
        request: OptimizationRequest,
        available_etfs: Optional[List[ETFWithDistributions]] = None
    ) -> OptimizationResult:
        """
        Optimize ETF portfolio to match desired allocations using CP-SAT solver.
        """
        
        # Get available ETFs if not provided
        if available_etfs is None:
            config = dict(request.config)
            available_etfs = await self._get_filtered_etfs(config)

        if not available_etfs:
            return OptimizationResult(
                etf_allocations=[],
                total_ter=0.0,
                achieved_countries={},
                achieved_industries={},
                optimization_score=0.0,
                country_unallocated=0.0,
                industry_unallocated=0.0
            )

        print(f"Optimizing with {len(available_etfs)} ETFs: {[etf.ticker for etf in available_etfs]}")

        # Get target allocations
        target_countries = {k: v for k, v in request.countries.items() if v > 0}
        target_industries = {k: v for k, v in request.industries.items() if v > 0}
        
        max_etfs = request.config.get('max_etfs', 10)
        
        # Use CP-SAT for discrete optimization
        model = cp_model.CpModel()
        
        # Decision variables: binary variables for ETF selection
        etf_selected = []
        for i, etf in enumerate(available_etfs):
            etf_selected.append(model.NewBoolVar(f'select_etf_{i}_{etf.ticker}'))
        
        # Weight variables: integer weights (0-100 representing percentages)
        etf_weights = []
        for i, etf in enumerate(available_etfs):
            etf_weights.append(model.NewIntVar(0, 100, f'weight_etf_{i}_{etf.ticker}'))
        
        # Constraint: limit number of selected ETFs
        model.Add(sum(etf_selected) <= max_etfs)
        model.Add(sum(etf_selected) >= 1)  # At least 1 ETF
        
        # Constraint: weights sum to 100 (100%)
        model.Add(sum(etf_weights) == 100)
        
        # Link selection and weights: if ETF not selected, weight must be 0
        for i in range(len(available_etfs)):
            model.Add(etf_weights[i] <= 100 * etf_selected[i])
            model.Add(etf_weights[i] >= 1 * etf_selected[i])  # If selected, at least 1%
        
        # Pre-calculate allocation matrices for efficiency
        country_allocations = {}
        for country in target_countries:
            country_allocations[country] = []
            for etf in available_etfs:
                allocation = 0
                for dist in etf.country_distributions:
                    if dist.country == country:
                        allocation = int(dist.weight * 100)  # Scale to integer (0-10000)
                        break
                country_allocations[country].append(allocation)
        
        industry_allocations = {}
        for industry in target_industries:
            industry_allocations[industry] = []
            for etf in available_etfs:
                allocation = 0
                for dist in etf.industry_distributions:
                    if dist.industry == industry:
                        allocation = int(dist.weight * 100)  # Scale to integer (0-10000)
                        break
                industry_allocations[industry].append(allocation)
        
        # Calculate achieved allocations using linear combinations
        achieved_countries = {}
        for country in target_countries:
            achieved_countries[country] = model.NewIntVar(0, 1000000, f'achieved_country_{country}')
            
            # achieved = sum(weight[i] * allocation[i] for i in range(num_etfs))
            weighted_contributions = []
            for i, etf in enumerate(available_etfs):
                if country_allocations[country][i] > 0:
                    contribution = model.NewIntVar(0, 1000000, f'contrib_{country}_{i}')
                    model.AddMultiplicationEquality(contribution, etf_weights[i], country_allocations[country][i])
                    weighted_contributions.append(contribution)
            
            if weighted_contributions:
                model.Add(achieved_countries[country] == sum(weighted_contributions))
            else:
                model.Add(achieved_countries[country] == 0)
        
        achieved_industries = {}
        for industry in target_industries:
            achieved_industries[industry] = model.NewIntVar(0, 1000000, f'achieved_industry_{industry}')
            
            weighted_contributions = []
            for i, etf in enumerate(available_etfs):
                if industry_allocations[industry][i] > 0:
                    contribution = model.NewIntVar(0, 1000000, f'contrib_{industry}_{i}')
                    model.AddMultiplicationEquality(contribution, etf_weights[i], industry_allocations[industry][i])
                    weighted_contributions.append(contribution)
            
            if weighted_contributions:
                model.Add(achieved_industries[industry] == sum(weighted_contributions))
            else:
                model.Add(achieved_industries[industry] == 0)
        
        # Objective: minimize allocation errors and TER
        objective_terms = []
        
        # Country allocation errors
        for country, target in target_countries.items():
            target_scaled = int(target * 10000)  # Scale target to match (weight * allocation)
            achieved = achieved_countries[country]
            
            # Create absolute difference variables
            pos_error = model.NewIntVar(0, 1000000, f'country_pos_error_{country}')
            neg_error = model.NewIntVar(0, 1000000, f'country_neg_error_{country}')
            
            model.Add(achieved - target_scaled <= pos_error)
            model.Add(target_scaled - achieved <= neg_error)
            
            # Add to objective with high weight
            objective_terms.append(pos_error)
            objective_terms.append(neg_error)
        
        # Industry allocation errors
        for industry, target in target_industries.items():
            target_scaled = int(target * 10000)
            achieved = achieved_industries[industry]
            
            pos_error = model.NewIntVar(0, 1000000, f'industry_pos_error_{industry}')
            neg_error = model.NewIntVar(0, 1000000, f'industry_neg_error_{industry}')
            
            model.Add(achieved - target_scaled <= pos_error)
            model.Add(target_scaled - achieved <= neg_error)
            
            # Add to objective with high weight for important industries
            weight_multiplier = 10 if target >= 20.0 else 5  # Higher penalty for major allocations
            objective_terms.extend([pos_error * weight_multiplier, neg_error * weight_multiplier])
        
        # TER minimization (convert to integer, multiply by 100 for precision)
        for i, etf in enumerate(available_etfs):
            ter_scaled = int(etf.ter * 10)  # Scale TER to integer (smaller scale for lower priority)
            ter_contribution = model.NewIntVar(0, 1000, f'ter_contrib_{i}')
            model.AddMultiplicationEquality(ter_contribution, etf_weights[i], ter_scaled)
            objective_terms.append(ter_contribution)  # Lower priority for TER
        
        # Set objective
        if objective_terms:
            model.Minimize(sum(objective_terms))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.log_search_progress = False
        
        status = solver.Solve(model)
        
        print(f"CP-SAT solve status: {status}")
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print("CP-SAT optimization failed, using fallback")
            return await self._fallback_optimization(available_etfs, target_countries, target_industries)
        
        # Extract solution
        selected_etfs = []
        selected_weights = []
        
        for i, etf in enumerate(available_etfs):
            if solver.Value(etf_selected[i]):
                weight = solver.Value(etf_weights[i]) / 100.0  # Convert back to fraction
                if weight >= 0.01:  # At least 1%
                    selected_etfs.append(etf)
                    selected_weights.append(weight)
        
        print(f"Selected ETFs: {[(etf.ticker, w) for etf, w in zip(selected_etfs, selected_weights)]}")
        
        # Calculate final allocations
        final_achieved_countries = self._calculate_achieved_allocations(
            selected_weights, selected_etfs, 'country'
        )
        final_achieved_industries = self._calculate_achieved_allocations(
            selected_weights, selected_etfs, 'industry'
        )
        
        # Calculate metrics
        total_ter = sum(w * etf.ter for w, etf in zip(selected_weights, selected_etfs))
        optimization_score = self._calculate_optimization_score(
            target_countries, final_achieved_countries, target_industries, final_achieved_industries
        )
        
        # Create ETF allocations
        etf_allocations = []
        for etf, weight in zip(selected_etfs, selected_weights):
            etf_allocations.append(ETFAllocation(
                etf_id=etf.id,
                name=etf.name,
                ticker=etf.ticker,
                weight=weight,
                ter=etf.ter
            ))
        
        return OptimizationResult(
            etf_allocations=etf_allocations,
            total_ter=total_ter,
            achieved_countries=final_achieved_countries,
            achieved_industries=final_achieved_industries,
            optimization_score=optimization_score,
            country_unallocated=final_achieved_countries.get('Unallocated', 0.0),
            industry_unallocated=final_achieved_industries.get('Unallocated', 0.0)
        )

    async def _get_filtered_etfs(self, config: Dict) -> List[ETFWithDistributions]:
        """Get filtered list of available ETFs based on config, optimized for CP-SAT."""
        max_ter = config.get('max_ter', 2.0)
        excluded_etfs = set(config.get('excluded_etfs', []))
        min_fund_size = config.get('min_fund_size', 100)  # 100M minimum
        categories = config.get('categories', None)  # Optional list of categories to include
        
        # Get a good pool of ETFs with relaxed fund size for diversity
        all_etfs = await self.db.get_etfs(
            limit=500,  # Get many candidates
            max_ter=max_ter,
            min_fund_size=min_fund_size * 0.5  # Relax fund size for sector/thematic ETFs
        )
        
        # Filter out excluded ETFs and ensure we have distributions
        filtered_etfs = []
        for etf in all_etfs:
            # Check category filter if specified
            if categories and etf.category and etf.category not in categories:
                continue
                
            if (etf.id not in excluded_etfs and 
                etf.ticker not in excluded_etfs and
                (etf.country_distributions or etf.industry_distributions)):
                filtered_etfs.append(etf)
        
        
        print(f"Selected diverse ETF pool:")
        for etf in filtered_etfs:
            energy_exp = sum(d.weight for d in etf.industry_distributions if d.industry == 'Energy')
            us_exp = sum(d.weight for d in etf.country_distributions if d.country == 'United States')
            print(f"  {etf.ticker}: Energy {energy_exp:.1f}%, US {us_exp:.1f}%, TER {etf.ter:.2f}%")

        return filtered_etfs

    async def _fallback_optimization(
        self,
        etfs: List[ETFWithDistributions],
        target_countries: Dict[str, float],
        target_industries: Dict[str, float]
    ) -> OptimizationResult:
        """Smart heuristic fallback when CP-SAT optimization fails."""
        
        print("Using fallback optimization algorithm")
        
        # Score each ETF based on how well it matches targets
        etf_scores = []
        
        for etf in etfs:
            score = 0.0
            
            # Country matching score
            for dist in etf.country_distributions:
                target_weight = target_countries.get(dist.country, 0.0)
                if target_weight > 0:
                    match_score = min(dist.weight, target_weight) * 2.0
                    score += match_score
            
            # Industry matching score  
            for dist in etf.industry_distributions:
                target_weight = target_industries.get(dist.industry, 0.0)
                if target_weight > 0:
                    match_score = min(dist.weight, target_weight) * 2.0
                    score += match_score
            
            # Penalty for high TER
            score -= etf.ter * 10.0
            
            etf_scores.append((etf, max(0.0, score)))
        
        # Sort by score and select top ETFs
        etf_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select top 5 ETFs with equal weights
        selected_etfs = [etf for etf, score in etf_scores[:5] if score > 0]
        if not selected_etfs:
            selected_etfs = etfs[:3]  # Fallback to first 3 ETFs
        
        selected_weights = [1.0 / len(selected_etfs)] * len(selected_etfs)
        
        print(f"Fallback selected: {[(etf.ticker, w) for etf, w in zip(selected_etfs, selected_weights)]}")
        
        # Calculate results
        achieved_countries = self._calculate_achieved_allocations(selected_weights, selected_etfs, 'country')
        achieved_industries = self._calculate_achieved_allocations(selected_weights, selected_etfs, 'industry')
        
        total_ter = sum(w * etf.ter for w, etf in zip(selected_weights, selected_etfs))
        optimization_score = self._calculate_optimization_score(
            target_countries, achieved_countries, target_industries, achieved_industries
        )
        
        etf_allocations = [
            ETFAllocation(
                etf_id=etf.id,
                name=etf.name,
                ticker=etf.ticker,
                weight=weight,
                ter=etf.ter
            )
            for etf, weight in zip(selected_etfs, selected_weights)
        ]
        
        return OptimizationResult(
            etf_allocations=etf_allocations,
            total_ter=total_ter,
            achieved_countries=achieved_countries,
            achieved_industries=achieved_industries,
            optimization_score=optimization_score,
            country_unallocated=achieved_countries.get('Unallocated', 0.0),
            industry_unallocated=achieved_industries.get('Unallocated', 0.0)
        )

    def _calculate_achieved_allocations(
        self, 
        weights: List[float], 
        etfs: List[ETFWithDistributions], 
        allocation_type: str
    ) -> Dict[str, float]:
        """Calculate achieved allocations for countries or industries."""
        achieved = {}
        
        for weight, etf in zip(weights, etfs):
            distributions = (etf.country_distributions 
                           if allocation_type == 'country' 
                           else etf.industry_distributions)
            
            for dist in distributions:
                category = dist.country if allocation_type == 'country' else dist.industry
                if category not in achieved:
                    achieved[category] = 0.0
                achieved[category] += weight * dist.weight
        
        return achieved

    def _calculate_optimization_score(
        self,
        target_countries: Dict[str, float],
        achieved_countries: Dict[str, float],
        target_industries: Dict[str, float],
        achieved_industries: Dict[str, float]
    ) -> float:
        """Calculate optimization score (0-1, higher is better)."""
        
        total_error = 0.0
        total_targets = 0.0
        
        # Country allocation errors
        for country, target in target_countries.items():
            if target > 0:  # Only consider non-zero targets
                achieved = achieved_countries.get(country, 0.0)
                error = abs(target - achieved)
                total_error += error
                total_targets += target
        
        # Industry allocation errors
        for industry, target in target_industries.items():
            if target > 0:  # Only consider non-zero targets
                achieved = achieved_industries.get(industry, 0.0)
                error = abs(target - achieved)
                total_error += error
                total_targets += target
        
        if total_targets == 0:
            return 1.0
        
        # Calculate score: 1 - (relative error)
        relative_error = total_error / total_targets
        return max(0.0, 1.0 - relative_error)

