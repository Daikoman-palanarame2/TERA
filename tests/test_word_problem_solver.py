import unittest
import sys
import os
from decimal import Decimal

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.solvers.plugins.word_problem_solver import WordProblemSolver
from app.core.exceptions import VerificationError

class TestWordProblemSolver(unittest.TestCase):
    def setUp(self):
        self.solver = WordProblemSolver()

    def test_inventory_success_standard(self):
        prompt = (
            "A warehouse starts with 1,200 units of stock. The inventory is reduced by 15% due to a promotion. "
            "Later, they restock by receiving 450 units, and then ship out 300 units to customers. How many units remain?"
        )
        res = self.solver.solve(prompt)
        # start = 1200
        # reduction = 1200 * 0.15 = 180
        # restock = 450
        # shipped = 300
        # remaining = 1200 - 180 + 450 - 300 = 1170
        self.assertEqual(res, "1170")

    def test_inventory_success_reordered(self):
        prompt = (
            "Later, they restock by receiving 450 units. A warehouse starts with 1,200 units of stock. "
            "Then, ship out 300 units to customers. The inventory is reduced by 15% of the starting stock. How many units remain?"
        )
        res = self.solver.solve(prompt)
        self.assertEqual(res, "1170")

    def test_public_inventory_quarter_labels_are_not_quantities(self):
        prompt = (
            "A warehouse starts with 2,400 units. In Q1 it sells 37% of stock. "
            "In Q2 it restocks 800 units. In Q3 it sells 640 units. How many remain?"
        )
        self.assertEqual(self.solver.solve(prompt), "1672")

    def test_inventory_unexplained_numbers(self):
        prompt = (
            "A warehouse starts with 1,200 units of stock. During a 7-day campaign, "
            "the inventory is reduced by 15% due to a promotion. "
            "Later, they restock by receiving 450 units, and then ship out 300 units to customers. How many units remain?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

    def test_inventory_ambiguous_percentage_base(self):
        prompt = (
            "A warehouse starts with 1,200 units of stock. The inventory is reduced by 15% from last month. "
            "Later, they restock by receiving 450 units, and then ship out 300 units to customers. How many units remain?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

    def test_inventory_negative_quantities(self):
        prompt = (
            "A warehouse starts with -1,200 units of stock. The inventory is reduced by 15% due to a promotion. "
            "Later, they restock by receiving 450 units, and then ship out 300 units to customers. How many units remain?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

    def test_recipe_success_fraction(self):
        prompt = (
            "A recipe requires 3/4 cups of sugar to make 24 cookies. If you want to make 36 cookies, "
            "and sugar costs $2.40 per cup, how much will the sugar cost?"
        )
        res = self.solver.solve(prompt)
        # sugar = (3/4) * 36 / 24 = 27/24 = 9/8 = 1.125 cups
        # cost = 1.125 * 2.40 = 2.70
        self.assertEqual(res, "The recipe requires 1.125 cups of sugar and will cost $2.70.")

    def test_recipe_success_mixed_fraction(self):
        prompt = (
            "A recipe requires 1 1/2 cups of sugar to make 10 servings. If you want to make 25 servings, "
            "and sugar costs $4.00 per cup, how much will the sugar cost?"
        )
        res = self.solver.solve(prompt)
        # sugar = 1.5 * 25 / 10 = 3.75 cups
        # cost = 3.75 * 4.00 = 15.00
        self.assertEqual(res, "The recipe requires 3.75 cups of sugar and will cost $15.00.")

    def test_recipe_success_decimal(self):
        prompt = (
            "A recipe requires 1.5 cups of sugar to make 10 servings. If you want to make 25 servings, "
            "and sugar costs $4.00 per cup, how much will the sugar cost?"
        )
        res = self.solver.solve(prompt)
        self.assertEqual(res, "The recipe requires 3.75 cups of sugar and will cost $15.00.")

    def test_public_recipe_uses_and_cost_at_phrasing(self):
        prompt = (
            "A recipe uses 2/3 cup for 8 servings. How many cups for 18 servings, "
            "and cost at $3 per cup?"
        )
        self.assertEqual(
            self.solver.solve(prompt),
            "The recipe requires 1.5 cups of sugar and will cost $4.50.",
        )

    def test_recipe_unexplained_numbers(self):
        prompt = (
            "A recipe requires 3/4 cups of sugar to make 24 cookies. If you want to make 36 cookies "
            "using a 12-inch bowl, and sugar costs $2.40 per cup, how much will the sugar cost?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

    def test_recipe_missing_cost(self):
        prompt = (
            "A recipe requires 3/4 cups of sugar to make 24 cookies. If you want to make 36 cookies, "
            "how much sugar will you need?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

    def test_recipe_units_mismatch(self):
        prompt = (
            "A recipe requires 3/4 cups of sugar to make 24 cookies. If you want to make 36 servings, "
            "and sugar costs $2.40 per cup, how much will the sugar cost?"
        )
        with self.assertRaises(VerificationError):
            self.solver.solve(prompt)

if __name__ == "__main__":
    unittest.main()
