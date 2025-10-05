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
            etf_selected.append(model.NewBoolVar(f'select_{i}'))
        
        # Weight variables: integer weights (0-100 representing percentages)
        # Using smaller scale for better performance
        etf_weights = []
        for i, etf in enumerate(available_etfs):
            etf_weights.append(model.NewIntVar(0, 100, f'w_{i}'))
        
        # Constraint: limit number of selected ETFs
        model.Add(sum(etf_selected) <= max_etfs)
        model.Add(sum(etf_selected) >= 1)  # At least 1 ETF
        
        # Constraint: weights sum to 100 (100%)
        model.Add(sum(etf_weights) == 100)
        
        # Link selection and weights: if ETF not selected, weight must be 0
        for i in range(len(available_etfs)):
            model.Add(etf_weights[i] <= 100 * etf_selected[i])
            model.Add(etf_weights[i] >= 1 * etf_selected[i])  # If selected, at least 1%
        
        # Pre-calculate allocation matrices for efficiency (sparse representation)
        # Only store non-zero allocations to reduce constraint complexity
        # Scale: Use integer representation (0-100 scale for percentages)
        country_allocations = {}
        for country in target_countries:
            sparse_alloc = []
            for i, etf in enumerate(available_etfs):
                for dist in etf.country_distributions:
                    if dist.country == country and dist.weight > 0.01:  # Filter negligible allocations
                        allocation = int(round(dist.weight))  # 0-100 scale
                        if allocation > 0:
                            sparse_alloc.append((i, allocation))
                        break
            country_allocations[country] = sparse_alloc
        
        industry_allocations = {}
        for industry in target_industries:
            sparse_alloc = []
            for i, etf in enumerate(available_etfs):
                for dist in etf.industry_distributions:
                    if dist.industry == industry and dist.weight > 0.01:  # Filter negligible allocations
                        allocation = int(round(dist.weight))  # 0-100 scale
                        if allocation > 0:
                            sparse_alloc.append((i, allocation))
                        break
            industry_allocations[industry] = sparse_alloc
        
        # Calculate achieved allocations using linear combinations (optimized)
        # Use LinearExpr.WeightedSum instead of multiplication constraints
        achieved_countries = {}
        for country in target_countries:
            sparse_alloc = country_allocations[country]
            
            if sparse_alloc:
                # Use weighted sum directly - much faster than multiplication constraints
                weighted_terms = []
                coefficients = []
                for etf_idx, allocation in sparse_alloc:
                    weighted_terms.append(etf_weights[etf_idx])
                    coefficients.append(allocation)
                
                achieved_var = model.NewIntVar(0, 10000, f'ac_{country[:10]}')
                model.Add(achieved_var == cp_model.LinearExpr.WeightedSum(weighted_terms, coefficients))
                achieved_countries[country] = achieved_var
            else:
                achieved_var = model.NewIntVar(0, 0, f'ac_{country[:10]}_zero')
                achieved_countries[country] = achieved_var
        
        achieved_industries = {}
        for industry in target_industries:
            sparse_alloc = industry_allocations[industry]
            
            if sparse_alloc:
                weighted_terms = []
                coefficients = []
                for etf_idx, allocation in sparse_alloc:
                    weighted_terms.append(etf_weights[etf_idx])
                    coefficients.append(allocation)
                
                achieved_var = model.NewIntVar(0, 10000, f'ai_{industry[:10]}')
                model.Add(achieved_var == cp_model.LinearExpr.WeightedSum(weighted_terms, coefficients))
                achieved_industries[industry] = achieved_var
            else:
                achieved_var = model.NewIntVar(0, 0, f'ai_{industry[:10]}_zero')
                achieved_industries[industry] = achieved_var
        
        # Objective: minimize allocation errors and TER (optimized with LinearExpr)
        objective_terms = []
        
        # Country allocation errors (using 100x scale: target*100 vs achieved weight*allocation)
        for country, target in target_countries.items():
            target_scaled = int(round(target * 100))  # Scale to match weight*allocation scale
            achieved = achieved_countries[country]
            
            # Create absolute difference variables
            pos_error = model.NewIntVar(0, 10000, f'cpe_{country[:5]}')
            neg_error = model.NewIntVar(0, 10000, f'cne_{country[:5]}')
            
            model.Add(achieved - target_scaled <= pos_error)
            model.Add(target_scaled - achieved <= neg_error)
            
            # Add to objective with high weight
            objective_terms.append(pos_error * 100)
            objective_terms.append(neg_error * 100)
        
        # Industry allocation errors
        for industry, target in target_industries.items():
            target_scaled = int(round(target * 100))
            achieved = achieved_industries[industry]
            
            pos_error = model.NewIntVar(0, 10000, f'ipe_{industry[:5]}')
            neg_error = model.NewIntVar(0, 10000, f'ine_{industry[:5]}')
            
            model.Add(achieved - target_scaled <= pos_error)
            model.Add(target_scaled - achieved <= neg_error)
            
            # Add to objective with high weight for important industries
            weight_multiplier = 1000 if target >= 20.0 else 500  # Higher penalty for major allocations
            objective_terms.extend([pos_error * weight_multiplier, neg_error * weight_multiplier])
        
        # TER minimization using weighted sum (no intermediate variables needed)
        ter_coefficients = [int(round(etf.ter * 10)) for etf in available_etfs]
        ter_term = cp_model.LinearExpr.WeightedSum(etf_weights, ter_coefficients)
        objective_terms.append(ter_term)
        
        # Set objective
        if objective_terms:
            model.Minimize(sum(objective_terms))
        
        # Solve with optimized parameters
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0  # Reduced timeout - should solve faster now
        solver.parameters.log_search_progress = False
        solver.parameters.num_search_workers = 4  # Parallel search
        solver.parameters.linearization_level = 2  # Better constraint linearization
        
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

