"""Infraestrutura do HUD: sem dependência de Qt, usável por GUI, servidor web e CLI.

Regra de ouro: nenhum módulo fora de ``core.proc`` pode importar ``subprocess``.
Isso garante que nenhuma janela de console apareça no Windows (veja ``tests/``).
"""
