"""Tests for slicing allocation engine."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicing.allocation_engine import AllocationEngine
from slicing.context_engine import ContextEngine
from traffic_models.demand_generator import DemandGenerator


def test_allocation_normal():
    engine = AllocationEngine()
    ctx = ContextEngine()
    demands = DemandGenerator().get_demands("normal")
    priorities = ctx.get_context("normal")
    allocation = engine.allocate(100, priorities, demands)
    assert sum(allocation.values()) <= 100.01
    assert len(allocation) == 4


def test_allocation_disaster_prioritizes_healthcare():
    engine = AllocationEngine()
    ctx = ContextEngine()
    demands = DemandGenerator().get_demands("disaster")
    priorities = ctx.get_context("disaster")
    allocation = engine.allocate(100, priorities, demands)
    assert allocation["healthcare"] >= allocation["general"]


def test_allocation_school_prioritizes_education():
    engine = AllocationEngine()
    ctx = ContextEngine()
    demands = DemandGenerator().get_demands("school")
    priorities = ctx.get_context("school")
    allocation = engine.allocate(100, priorities, demands)
    assert allocation["education"] > allocation["agriculture"]


if __name__ == "__main__":
    test_allocation_normal()
    test_allocation_disaster_prioritizes_healthcare()
    test_allocation_school_prioritizes_education()
    print("All allocation tests passed.")
