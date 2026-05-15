"""Prefect flow definitions for pipeline stages."""

from domain_kg.flows.main import characterize_domain

__all__ = ["characterize_domain"]
