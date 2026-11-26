"""Palavras que contam num texto, para a busca por palavras do repositório em memória.

O Postgres faz isso melhor, com o dicionário de português dele (ver repositorio_postgres.py).
Aqui é uma aproximação simples e determinística, usada nos testes e sem banco.
"""

import re
import unicodedata

_VAZIAS = frozenset(
    "a o e de da do das dos em no na nos nas um uma uns umas para por com que qual quais como "
    "ser sao tem voce voces os as ao aos se ou mais mas nao sim eu me meu minha foi ha ja ate "
    "isso esse essa este esta e eh la".split()
)


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra))


def termos(texto: str) -> set[str]:
    """Minúsculas, sem acento, sem palavras vazias, cortadas num radical curto."""
    palavras = re.findall(r"[a-z0-9]+", sem_acento(texto))
    return {_radical(palavra) for palavra in palavras if palavra not in _VAZIAS}


def _radical(palavra: str) -> str:
    # "horas" e "horario" viram "hora"; "abrem" e "abrimos" viram "abr". Número fica inteiro.
    if palavra.isdigit():
        return palavra
    return palavra[:4] if len(palavra) > 5 else palavra[:3] if len(palavra) > 3 else palavra


def cobertura(pergunta: str, trecho: str) -> float:
    """Que fração das palavras da pergunta aparece no trecho, de 0 a 1."""
    da_pergunta = termos(pergunta)
    if not da_pergunta:
        return 0.0
    return len(da_pergunta & termos(trecho)) / len(da_pergunta)
