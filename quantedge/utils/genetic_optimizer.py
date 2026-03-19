# utils/genetic_optimizer.py
import numpy as np
import random
from typing import Dict, List, Tuple

class GeneticOptimizer:
    """
    Genetic Algorithm to optimize trading parameters.
    Uses evolution to find optimal risk_per_trade, atr_multiplier, confidence_threshold, etc.
    """
    def __init__(self, population_size=50, generations=100, mutation_rate=0.1):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.best_individual = None
        self.best_fitness = float('-inf')

    def create_individual(self) -> Dict:
        """Create a random trading strategy configuration"""
        return {
            'risk_per_trade': random.uniform(0.01, 0.05),  # 1-5% risk
            'atr_multiplier': random.uniform(1.0, 3.0),     # SL distance
            'confidence_threshold': random.uniform(0.50, 0.75),  # Min confidence
            'tp_ratio': random.uniform(1.2, 2.5),           # Risk:Reward
            'max_trades_per_day': random.randint(3, 15),
            'volatility_filter': random.uniform(0.5, 1.5),  # ATR filter
        }

    def create_population(self) -> List[Dict]:
        """Create initial population"""
        return [self.create_individual() for _ in range(self.population_size)]

    def fitness_function(self, individual: Dict, backtest_results: Dict) -> float:
        """
        Calculate fitness score based on backtest results.
        Higher score = better strategy.

        backtest_results should contain:
        - total_return: % return
        - sharpe_ratio: Risk-adjusted return
        - max_drawdown: Worst loss
        - win_rate: % winning trades
        - profit_factor: Gross profit / Gross loss
        """
        if backtest_results is None:
            return 0.0

        # Multi-objective fitness function
        total_return = backtest_results.get('total_return', 0)
        sharpe = backtest_results.get('sharpe_ratio', 0)
        max_dd = backtest_results.get('max_drawdown', -100)
        win_rate = backtest_results.get('win_rate', 0)
        profit_factor = backtest_results.get('profit_factor', 0)

        # Penalize high drawdown heavily
        drawdown_penalty = max(0, 1 - abs(max_dd) / 20)  # -20% DD = 0 penalty score

        # Weighted fitness
        fitness = (
            total_return * 0.30 +
            sharpe * 10 * 0.25 +
            drawdown_penalty * 100 * 0.20 +
            win_rate * 0.15 +
            profit_factor * 10 * 0.10
        )

        return fitness

    def crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """Create two offspring from two parents"""
        child1 = {}
        child2 = {}

        for key in parent1.keys():
            if random.random() > 0.5:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]

        return child1, child2

    def mutate(self, individual: Dict) -> Dict:
        """Randomly mutate an individual"""
        mutated = individual.copy()

        if random.random() < self.mutation_rate:
            mutated['risk_per_trade'] = random.uniform(0.01, 0.05)

        if random.random() < self.mutation_rate:
            mutated['atr_multiplier'] = random.uniform(1.0, 3.0)

        if random.random() < self.mutation_rate:
            mutated['confidence_threshold'] = random.uniform(0.50, 0.75)

        if random.random() < self.mutation_rate:
            mutated['tp_ratio'] = random.uniform(1.2, 2.5)

        if random.random() < self.mutation_rate:
            mutated['max_trades_per_day'] = random.randint(3, 15)

        if random.random() < self.mutation_rate:
            mutated['volatility_filter'] = random.uniform(0.5, 1.5)

        return mutated

    def select_parents(self, population: List[Dict], fitness_scores: List[float]) -> Tuple[Dict, Dict]:
        """Tournament selection"""
        tournament_size = 5

        def tournament():
            contestants = random.sample(list(zip(population, fitness_scores)), tournament_size)
            winner = max(contestants, key=lambda x: x[1])
            return winner[0]

        parent1 = tournament()
        parent2 = tournament()
        return parent1, parent2

    def evolve(self, backtest_function):
        """
        Main evolution loop.

        backtest_function: A function that takes an individual (strategy params)
                          and returns backtest results dict
        """
        print("🧬 Genetic Algorithm: Starting Evolution...")
        print(f"Population: {self.population_size} | Generations: {self.generations}")

        population = self.create_population()

        for generation in range(self.generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                backtest_results = backtest_function(individual)
                fitness = self.fitness_function(individual, backtest_results)
                fitness_scores.append(fitness)

            # Track best
            best_idx = np.argmax(fitness_scores)
            if fitness_scores[best_idx] > self.best_fitness:
                self.best_fitness = fitness_scores[best_idx]
                self.best_individual = population[best_idx].copy()

            if generation % 10 == 0:
                avg_fitness = np.mean(fitness_scores)
                print(f"Gen {generation}: Best Fitness: {self.best_fitness:.2f} | Avg: {avg_fitness:.2f}")

            # Create next generation
            new_population = []

            # Elitism: Keep top 10%
            elite_count = max(1, self.population_size // 10)
            elite_indices = np.argsort(fitness_scores)[-elite_count:]
            for idx in elite_indices:
                new_population.append(population[idx].copy())

            # Fill rest with offspring
            while len(new_population) < self.population_size:
                parent1, parent2 = self.select_parents(population, fitness_scores)
                child1, child2 = self.crossover(parent1, parent2)

                child1 = self.mutate(child1)
                child2 = self.mutate(child2)

                new_population.append(child1)
                if len(new_population) < self.population_size:
                    new_population.append(child2)

            population = new_population

        print("\n🧬 Evolution Complete!")
        print(f"Best Fitness: {self.best_fitness:.2f}")
        print(f"Best Parameters: {self.best_individual}")

        return self.best_individual

    def get_best_params(self) -> Dict:
        """Return the best parameters found"""
        return self.best_individual
