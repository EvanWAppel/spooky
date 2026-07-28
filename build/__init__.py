"""Offline data pipeline. Run order lives in build/__main__.py, not filenames.

Nothing in here runs at request time — the app only ever reads the committed
dataset (PRD §8).
"""
