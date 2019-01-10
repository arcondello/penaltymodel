import unittest
import itertools

import dimod
import dwave_networkx as dnx
import networkx as nx

from pysmt.environment import get_env, reset_env

import penaltymodel.core as pm
import penaltymodel.maxgap as maxgap


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.env = reset_env()

    def generate_and_check(self, graph, configurations, decision_variables,
                           linear_energy_ranges, quadratic_energy_ranges,
                           min_classical_gap):

        bqm, gap = maxgap.generate(graph, configurations, decision_variables,
                                   linear_energy_ranges,
                                   quadratic_energy_ranges,
                                   min_classical_gap)

        # check that the bqm/graph have the same structure
        self.assertEqual(len(bqm.linear), len(graph.nodes))
        for v in bqm.linear:
            self.assertIn(v, graph.nodes)
        self.assertEqual(len(bqm.quadratic), len(graph.edges))
        for u, v in bqm.quadratic:
            self.assertIn((u, v), graph.edges)

        # now solve for the thing
        sampleset = dimod.ExactSolver().sample(bqm)

        # check that ground has 0 energy
        if len(sampleset):
            self.assertAlmostEqual(sampleset.first.energy, min(configurations.values()))

        # check gap and other energies
        best_gap = float('inf')
        seen = set()
        for sample, energy in sampleset.data(['sample', 'energy']):
            config = tuple(sample[v] for v in decision_variables)

            # we want the minimum energy for each config of the decisison variables,
            # so once we've seen it once we can skip
            if config in seen:
                continue

            if config in configurations:
                self.assertAlmostEqual(energy, configurations[config])
                seen.add(config)
            else:
                best_gap = min(best_gap, energy)

        # check energy ranges
        for v, bias in bqm.linear.items():
            min_, max_ = linear_energy_ranges[v]
            self.assertGreaterEqual(bias, min_)
            self.assertLessEqual(bias, max_)

        for (u, v), bias in bqm.quadratic.items():
            min_, max_ = quadratic_energy_ranges.get((u, v), quadratic_energy_ranges.get((v, u), None))
            self.assertGreaterEqual(bias, min_)
            self.assertLessEqual(bias, max_)

    def test_disjoint(self):
        graph = dnx.chimera_graph(1, 1, 3)
        graph.add_edge(8, 9)

        configurations = {(-1, -1, -1): 0,
                          (+1, +1, -1): 0}
        decision_variables = (0, 1, 8)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_disjoint_decision_accross_subgraphs(self):
        graph = dnx.chimera_graph(1, 1, 3)
        graph.add_edge(8, 9)

        configurations = {(-1, -1, +1, -1): 0,
                          (+1, +1, -1, -1): 0}
        decision_variables = (0, 1, 3, 8)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_empty(self):
        # this should test things like empty graphs and empty configs
        graph = nx.Graph()
        configurations = {}
        decision_variables = tuple()
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_impossible(self):
        graph = nx.path_graph(3)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        decision_variables = (0, 1, 2)
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        with self.assertRaises(pm.ImpossiblePenaltyModel):
            maxgap.generate(graph, configurations, decision_variables,
                            linear_energy_ranges,
                            quadratic_energy_ranges,
                            min_classical_gap)

    def test_K1(self):
        graph = nx.complete_graph(1)
        configurations = {(+1,): 0}
        decision_variables = [0]
        linear_energy_ranges = {0: (-2, 2)}
        quadratic_energy_ranges = {}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_K1_multiple_energies(self):
        graph = nx.complete_graph(1)
        configurations = {(+1,): .1, (-1,): -.3}
        decision_variables = [0]
        linear_energy_ranges = {0: (-2, 2)}
        quadratic_energy_ranges = {}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_K33(self):
        graph = nx.Graph()
        for i in range(3):
            for j in range(3, 6):
                graph.add_edge(i, j)

        decision_variables = (0, 2, 3)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_K3_one_aux(self):
        graph = nx.complete_graph(3)

        configurations = {(-1, -1): 0, (1, 1): 0}

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        decision_variables = [0, 1]
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_K4(self):
        graph = nx.complete_graph(4)

        configurations = {(-1, -1, -1, -1): 0, (1, 1, 1, 1): 0}
        decision_variables = list(graph)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 1

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)

    def test_restricted_energy_ranges(self):
        """Create asymmetric energy ranges and test against that."""
        graph = dnx.chimera_graph(1, 1, 3)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        decision_variables = (0, 1, 2)
        linear_energy_ranges = {v: (-1., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., .5) for u, v in graph.edges}
        min_classical_gap = 2

        self.generate_and_check(graph, configurations, decision_variables,
                                linear_energy_ranges,
                                quadratic_energy_ranges,
                                min_classical_gap)


class TestGenerationLegacy(unittest.TestCase):
    """old testing framework"""
    def check_generated_ising_model(self, feasible_configurations, decision_variables,
                                    linear, quadratic, ground_energy, infeasible_gap):
        """Check that the given Ising model has the correct energy levels"""
        if not feasible_configurations:
            return

        response = dimod.ExactSolver().sample_ising(linear, quadratic)

        # samples are returned in order of energy
        sample, ground = next(iter(response.data(['sample', 'energy'])))
        gap = float('inf')

        self.assertIn(tuple(sample[v] for v in decision_variables), feasible_configurations)

        seen_configs = set()

        for sample, energy in response.data(['sample', 'energy']):
            config = tuple(sample[v] for v in decision_variables)

            # we want the minimum energy for each config of the decisison variables,
            # so once we've seen it once we can skip
            if config in seen_configs:
                continue

            if config in feasible_configurations:
                self.assertAlmostEqual(energy, ground)
                seen_configs.add(config)
            else:
                gap = min(gap, energy - ground)

        self.assertAlmostEqual(ground_energy, ground)
        self.assertAlmostEqual(gap, infeasible_gap)

    def test_negative_min_gap_impossible_bqm(self):
        """XOR Gate problem without auxiliary variables
        Note: Regardless of the negative gap, this BQM should remain impossible.
        """
        negative_gap = -3
        decision_variables = ['a', 'b', 'c']
        xor_gate = {(-1, -1, -1): 0,
                    (-1, 1, 1): 0,
                    (1, -1, 1): 0,
                    (1, 1, -1): 0}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        with self.assertRaises(pm.ImpossiblePenaltyModel):
            maxgap.generate_ising(graph, xor_gate, decision_variables,
                                  linear_energy_ranges,
                                  quadratic_energy_ranges,
                                  negative_gap,
                                  None)

    def test_negative_min_gap_feasible_bqm(self):
        # Regardless of the negative min classical gap, this feasible BQM should return its usual
        # max classical gap.
        negative_gap = -2
        decision_variables = ['a']
        config = {(-1,): 0}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        h, J, offset, gap = maxgap.generate_ising(graph, config, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  negative_gap,
                                                  None)

        expected_gap = 2
        self.assertEqual(expected_gap, gap)
        self.check_generated_ising_model(config, decision_variables, h, J, offset, gap)

    def test_min_gap_no_aux(self):
        """Verify min_classical_gap parameter works
        """
        # Set up problem
        decision_variables = ['a', 'b', 'c']
        or_gate = {(-1, -1, -1): 0,
                   (-1, 1, 1): 0,
                   (1, -1, 1): 0,
                   (1, 1, 1): 0}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        # Run problem with a min_classical_gap that is too large
        with self.assertRaises(pm.ImpossiblePenaltyModel):
            large_min_gap = 3
            maxgap.generate_ising(graph, or_gate, decision_variables,
                                  linear_energy_ranges,
                                  quadratic_energy_ranges,
                                  large_min_gap,
                                  None)

        # Lowering min_classical_gap should lead to a bqm being found
        smaller_min_gap = 1.5
        h, J, offset, gap = maxgap.generate_ising(graph, or_gate, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  smaller_min_gap,
                                                  None)
        self.assertGreaterEqual(gap, smaller_min_gap)
        self.check_generated_ising_model(or_gate, decision_variables, h, J, offset, gap)

    def test_min_gap_with_aux(self):
        """Verify min_classical_gap parameter works
        """
        decision_variables = ['a', 'b', 'c']
        xor_gate = {(-1, -1, -1): 0,
                    (-1, 1, 1): 0,
                    (1, -1, 1): 0,
                    (1, 1, -1): 0}
        graph = nx.complete_graph(decision_variables + ['aux0'])

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        # Run problem with a min_classical_gap that is too large
        with self.assertRaises(pm.ImpossiblePenaltyModel):
            large_min_gap = 2
            maxgap.generate_ising(graph, xor_gate, decision_variables,
                                  linear_energy_ranges,
                                  quadratic_energy_ranges,
                                  large_min_gap,
                                  None)

        # Lowering min_classical_gap should lead to a bqm being found
        smaller_min_gap = 0.5
        h, J, offset, gap = maxgap.generate_ising(graph, xor_gate, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  smaller_min_gap,
                                                  None)
        self.assertGreaterEqual(gap, smaller_min_gap)
        self.check_generated_ising_model(xor_gate, decision_variables, h, J, offset, gap)

    def test_min_gap_equals_max_gap(self):
        # Make sure that a model is always grabbed, even when min_gap == max_gap
        min_gap = 2     # This value is also the max classical gap
        decision_variables = ['a']
        config = {(-1,): -1}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        h, J, offset, gap = maxgap.generate_ising(graph, config, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_gap,
                                                  None)

        # Check that a model was found
        self.assertIsNotNone(h)
        self.assertIsNotNone(J)
        self.assertIsNotNone(offset)
        self.assertEqual(min_gap, gap)  # Min gap is also the max classical gap in this case
