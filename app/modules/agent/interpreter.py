"""Parsing local: uma condição numérica explícita por pergunta.

Não produz SQL nem tenta interpretar frases que não estejam no vocabulário.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import unicodedata

EXPRESSOES = {
    "no minimo": ">=",
    "no maximo": "<=",
    "abaixo de": "<",
    "menor que": "<",
    "inferior a": "<",
    "menos de": "<",
    "acima de": ">",
    "maior que": ">",
    "superior a": ">",
    "mais de": ">",
    "igual a": "=",
    "exatamente": "=",
}
OPERADORES = "|".join(re.escape(p) for p in sorted(EXPRESSOES, key=len, reverse=True))
PADRAO = re.compile(
    rf"(?<!\w)(?P<campo>quantidade\s+em\s+estoque|estoque|preco|valor)"
    rf"\s+(?P<operador>{OPERADORES})\s+"
    rf"(?P<valor>\d+(?:[.,]\d{{1,2}})?)(?!\w)",
    re.IGNORECASE,
)

@dataclass(frozen=True)
class ConsultaInterpretada:
    intencao: str
    campo: str
    operador: str
    valor: int | Decimal


def _normalizar(texto: str) -> str:
    sem_acentos = "".join(
        char for char in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(char)
    )
    return " ".join(sem_acentos.split())


def interpretar(pergunta: str) -> ConsultaInterpretada:
    texto = _normalizar(pergunta)
    # Múltiplas condições e negações requerem interpretação mais complexa.
    if re.search(r"\b(e|ou|nao|exceto)\b", texto):
        raise ValueError("A primeira versão aceita apenas uma condição afirmativa por pergunta.")
    encontrados = list(PADRAO.finditer(texto))
    if len(encontrados) != 1:
        raise ValueError("Pergunta não reconhecida. Informe estoque ou preço, comparação e valor.")
    match = encontrados[0]
    # Não interpretar parcialmente valores que não foram compreendidos.
    numeros = re.findall(r"\d+(?:[.,]\d+)?", texto)
    if len(numeros) != 1 or numeros[0] != match.group("valor"):
        raise ValueError("A pergunta deve conter apenas o valor numérico da condição.")
    if re.search(r"\d+[.,]\d{3,}", texto):
        raise ValueError("Use números sem separador de milhar; para preço, use até duas casas decimais.")

    campo = "preco" if match.group("campo") in {"preco", "valor"} else "quantidade_em_estoque"
    operador = EXPRESSOES[match.group("operador")]
    bruto = match.group("valor").replace(",", ".")
    try:
        if campo == "quantidade_em_estoque":
            if "." in bruto:
                raise ValueError("Quantidade em estoque deve ser um número inteiro.")
            valor: int | Decimal = int(bruto)
        else:
            valor = Decimal(bruto)
            if valor > Decimal("9999999999.99"):
                raise ValueError("Preço acima do limite permitido.")
    except InvalidOperation as exc:
        raise ValueError("Valor numérico inválido.") from exc

    return ConsultaInterpretada(
        intencao="consultar_estoque" if campo == "quantidade_em_estoque" else "consultar_produtos",
        campo=campo,
        operador=operador,
        valor=valor,
    )
