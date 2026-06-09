#!/usr/bin/env python3
"""LAAP Launcher - portable entry point"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from laap.api.cli import main
main()
