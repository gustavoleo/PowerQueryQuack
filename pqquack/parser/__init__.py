"""Power Query (M) lexer + parser producing an AST (goal section 4.1).

Targets the M subset needed for dependency analysis and the goal section 25
scenarios first (``let .. in`` blocks, query references, function invocation),
expanding iteratively. Unknown constructs are tolerated rather than guessed.
"""

from pqquack.parser.ast import Query, Step
from pqquack.parser.lexer import Token, TokenType, tokenize
from pqquack.parser.parser import parse_query

__all__ = ["Query", "Step", "Token", "TokenType", "tokenize", "parse_query"]
