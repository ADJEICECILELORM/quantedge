# optimizer/genetic_algorithm.py - Constrained Genetic Algorithm
"""
Constrained Genetic Algorithm for Parameter Optimization.

ONLY Optimizes:
✓ Parameters (stop-loss multiplier, take-profit ratio)
✓ Weights (RAG weight, math weight, news vs technical)
✓ Thresholds (confidence threshold, VPIN threshold, correlation max)
✓ Strategy selection (which regime uses which model)

EXPLICITLY FORBIDS:
✗ Random formula invention
✗ Unconstrained indicator mixing
✗ Data source modification
✗ RAG logic changes
✗ Execution engine changes
"""

import logging
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from copy import deepcopy

from optimizer.fitness_functions import FitnessFunction

logger = logging.getLogger(__name__)


@dataclass
class GeneDefinition:
    """Definition of a single gene (parameter to optimize)"""
    name: str
    min_value: float
    max_value: float
    current_value: float
    step_size: float = 0.01  # Minimum mutation step


@dataclass
class Chromosome:
    """
    Chromosome representing a complete parameter set.

    Each gene is a parameter value within defined bounds.
    """
    genes: Dict[str, float]  # gene_name -> value
    fitness: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'genes': self.genes,
            'fitness': self.fitness
        }


class ConstrainedGeneticAlgorithm:
    """
    Constrained GA that ONLY optimizes pre-defined parameters.

    Safe by design:
    - Cannot invent new formulas
    - Cannot modify data sources
    - Cannot change core logic
    - Only tunes existing parameters within bounds
    """

    def __init__(
        self,
        gene_definitions: List[GeneDefinition],
        population_size: int = 50,
        elite_size: int = 5,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.7
    ):
        self.gene_definitions = {g.name: g for g in gene_definitions}
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

        self.population: List[Chromosome] = []
        self.generation = 0
        self.best_chromosome: Optional[Chromosome] = None

        # Fitness function
        self.fitness_func = FitnessFunction()

        # Constraints log
        self.constraints_enforced = []

    def initialize_population(self):
        """
        Initialize random population within gene bounds.
        """
        logger.info(f"Initializing population of {self.population_size}...")

        self.population = []

        for i in range(self.population_size):
            genes = {}

            for gene_name, gene_def in self.gene_definitions.items():
                # Random value within bounds
                value = np.random.uniform(gene_def.min_value, gene_def.max_value)
                genes[gene_name] = value

            chromosome = Chromosome(genes=genes)
            self.population.append(chromosome)

        logger.info(f"Population initialized with {len(self.gene_definitions)} genes per chromosome")

    def evaluate_fitness(
        self,
        chromosome: Chromosome,
        backtest_results: Dict
    ) -> float:
        """
        Evaluate fitness of chromosome using backtest results.

        Args:
            chromosome: Chromosome to evaluate
            backtest_results: Results from backtesting with these parameters

        Returns:
            Fitness score (0-1)
        """
        returns = backtest_results.get('returns', [])
        trades = backtest_results.get('trades', [])
        regime_performance = backtest_results.get('regime_performance', {})

        fitness = self.fitness_func.calculate_fitness(
            returns=returns,
            trades=trades,
            regime_performance=regime_performance
        )

        chromosome.fitness = fitness
        return fitness

    def select_parents(self) -> List[Chromosome]:
        """
        Select parents using tournament selection.

        Tournament selection:
        - Pick random subset
        - Choose best from subset
        - Repeat
        """
        parents = []
        tournament_size = 5

        for _ in range(self.population_size - self.elite_size):
            # Random tournament
            tournament = np.random.choice(self.population, size=tournament_size, replace=False)

            # Select best from tournament
            winner = max(tournament, key=lambda c: c.fitness)
            parents.append(deepcopy(winner))

        return parents

    def crossover(
        self,
        parent1: Chromosome,
        parent2: Chromosome
    ) -> Tuple[Chromosome, Chromosome]:
        """
        Crossover two parents to create offspring.

        Uses uniform crossover (each gene has 50% chance from each parent).
        """
        if np.random.rand() > self.crossover_rate:
            # No crossover
            return deepcopy(parent1), deepcopy(parent2)

        child1_genes = {}
        child2_genes = {}

        for gene_name in parent1.genes.keys():
            if np.random.rand() < 0.5:
                child1_genes[gene_name] = parent1.genes[gene_name]
                child2_genes[gene_name] = parent2.genes[gene_name]
            else:
                child1_genes[gene_name] = parent2.genes[gene_name]
                child2_genes[gene_name] = parent1.genes[gene_name]

        child1 = Chromosome(genes=child1_genes)
        child2 = Chromosome(genes=child2_genes)

        return child1, child2

    def mutate(self, chromosome: Chromosome) -> Chromosome:
        """
        Mutate chromosome within gene bounds.

        CONSTRAINED: Mutation cannot exceed gene min/max bounds.
        """
        for gene_name, value in chromosome.genes.items():
            if np.random.rand() < self.mutation_rate:
                gene_def = self.gene_definitions[gene_name]

                # Gaussian mutation
                mutation = np.random.normal(0, gene_def.step_size * 5)
                new_value = value + mutation

                # ENFORCE BOUNDS (critical for safety)
                new_value = max(gene_def.min_value, min(gene_def.max_value, new_value))

                chromosome.genes[gene_name] = new_value

                # Log constraint enforcement
                if new_value == gene_def.min_value or new_value == gene_def.max_value:
                    self.constraints_enforced.append({
                        'gene': gene_name,
                        'attempted_value': value + mutation,
                        'clamped_to': new_value
                    })

        return chromosome

    def evolve(self, generations: int, backtest_function):
        """
        Evolve population over multiple generations.

        Args:
            generations: Number of generations to evolve
            backtest_function: Function to backtest a chromosome
                               Takes chromosome, returns backtest_results Dict
        """
        logger.info(f"Starting evolution for {generations} generations...")

        for gen in range(generations):
            self.generation = gen + 1

            logger.info(f"\n{'='*60}")
            logger.info(f"Generation {self.generation}/{generations}")
            logger.info(f"{'='*60}")

            # Evaluate fitness for all chromosomes
            logger.info("Evaluating population fitness...")
            for i, chromosome in enumerate(self.population):
                # Backtest with these parameters
                backtest_results = backtest_function(chromosome)

                # Calculate fitness
                fitness = self.evaluate_fitness(chromosome, backtest_results)

                if (i + 1) % 10 == 0:
                    logger.info(f"  Evaluated {i+1}/{len(self.population)} chromosomes")

            # Sort by fitness
            self.population.sort(key=lambda c: c.fitness, reverse=True)

            # Track best
            if self.best_chromosome is None or self.population[0].fitness > self.best_chromosome.fitness:
                self.best_chromosome = deepcopy(self.population[0])
                logger.info(f"✨ New best fitness: {self.best_chromosome.fitness:.4f}")

            # Print generation stats
            self._print_generation_stats()

            # Selection
            # Keep elite (best performers)
            next_generation = self.population[:self.elite_size]

            # Select parents for breeding
            parents = self.select_parents()

            # Crossover and mutation
            offspring = []
            for i in range(0, len(parents) - 1, 2):
                child1, child2 = self.crossover(parents[i], parents[i+1])
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                offspring.extend([child1, child2])

            # New population
            self.population = next_generation + offspring[:self.population_size - self.elite_size]

        logger.info(f"\n{'='*60}")
        logger.info(f"Evolution complete after {generations} generations")
        logger.info(f"Best fitness: {self.best_chromosome.fitness:.4f}")
        logger.info(f"{'='*60}")

        return self.best_chromosome

    def _print_generation_stats(self):
        """Print statistics for current generation"""
        fitnesses = [c.fitness for c in self.population]

        print(f"\n📊 Generation {self.generation} Statistics:")
        print(f"   Best Fitness: {max(fitnesses):.4f}")
        print(f"   Avg Fitness: {np.mean(fitnesses):.4f}")
        print(f"   Worst Fitness: {min(fitnesses):.4f}")
        print(f"   Std Dev: {np.std(fitnesses):.4f}")

        if self.constraints_enforced:
            print(f"   Constraints Enforced: {len(self.constraints_enforced)} (gene bounds respected)")

    def export_config(
        self,
        chromosome: Chromosome,
        filepath: str = "data/config_ga.json"
    ):
        """
        Export chromosome to config file.

        Args:
            chromosome: Chromosome to export
            filepath: Path to config file
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            config = {
                'generation': self.generation,
                'fitness': chromosome.fitness,
                'parameters': chromosome.genes,
                'gene_definitions': {
                    name: {
                        'min': gene.min_value,
                        'max': gene.max_value,
                        'step': gene.step_size
                    }
                    for name, gene in self.gene_definitions.items()
                },
                'ga_settings': {
                    'population_size': self.population_size,
                    'elite_size': self.elite_size,
                    'mutation_rate': self.mutation_rate,
                    'crossover_rate': self.crossover_rate
                }
            }

            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"✅ Config exported to {filepath}")
            print(f"\n💾 Optimized parameters saved to {filepath}")
            print(f"   Fitness: {chromosome.fitness:.4f}")
            print(f"   Generation: {self.generation}")

        except Exception as e:
            logger.error(f"Error exporting config: {e}")

    def load_config(self, filepath: str = "data/config_ga.json") -> Optional[Chromosome]:
        """Load chromosome from config file"""
        try:
            if not os.path.exists(filepath):
                return None

            with open(filepath, 'r') as f:
                config = json.load(f)

            chromosome = Chromosome(
                genes=config['parameters'],
                fitness=config.get('fitness', 0.0)
            )

            self.generation = config.get('generation', 0)

            logger.info(f"Loaded config from {filepath} (generation {self.generation})")

            return chromosome

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None


def get_default_gene_definitions() -> List[GeneDefinition]:
    """
    Get default gene definitions for QuantEdge V6.

    These are the parameters that GA can optimize.
    """
    return [
        # Stop loss and take profit
        GeneDefinition("stop_loss_atr_mult", 1.0, 3.0, 1.5, 0.1),
        GeneDefinition("take_profit_ratio", 1.0, 3.0, 2.0, 0.1),

        # RAG thresholds
        GeneDefinition("rag_similarity_threshold", 0.5, 0.9, 0.7, 0.05),
        GeneDefinition("news_confidence_threshold", 0.4, 0.8, 0.6, 0.05),
        GeneDefinition("news_impact_min", 0.3, 0.7, 0.5, 0.05),

        # Strategy weights
        GeneDefinition("rag_weight", 0.3, 0.7, 0.5, 0.05),
        GeneDefinition("math_weight", 0.3, 0.7, 0.5, 0.05),

        # VPIN threshold
        GeneDefinition("vpin_percentile_threshold", 85.0, 95.0, 90.0, 1.0),

        # Correlation max
        GeneDefinition("max_correlation_exposure", 0.6, 0.8, 0.7, 0.05),

        # Kelly fraction
        GeneDefinition("kelly_fraction", 0.15, 0.35, 0.25, 0.05),

        # Regime multipliers
        GeneDefinition("trend_position_mult", 0.8, 1.5, 1.2, 0.1),
        GeneDefinition("volatility_position_mult", 0.8, 1.5, 1.3, 0.1),
        GeneDefinition("reversion_position_mult", 0.6, 1.2, 1.0, 0.1),
        GeneDefinition("low_vol_position_mult", 0.3, 0.8, 0.5, 0.1),
    ]
