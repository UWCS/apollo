from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content

from utils import get_name_string

ERROR_LIMIT = 3
DEPTH_LIMIT = 50

LONG_HELP_TEXT = """
Inteprets and reduces pure lambda calculus statements.
Inputs are limited to a single line with a reduction limit of """ + str(DEPTH_LIMIT) + """.

Syntax:
  abstraction: \\x.y
  application: x y  OR  (x y)
  variable:    <any string not containing \\, ., (, ), or white space>

Example:
  !lambda eval (\\x.x) y                   -> y
  !lambda eval (\\x.\\y.y x) a b            -> (b a)
  !lambda eval \\f.(\\x.f(x x)) (\\x.f(x x)) -> <diverges>
"""

SHORT_HELP_TEXT = """Inteprets and reduces lambda calculus expressions."""


class Lcalc:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT, name="lambda")
    async def lcalc(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @lcalc.command(help="Evaluates a lambda expression.")
    async def eval(self, ctx: Context, *args: clean_content):
        display_name = get_name_string(ctx.message)
        self.errors = 0
        self.out = f'{display_name}:\n```'
        self.evaluate(" ".join(args))
        if self.errors:
            self.out += f'{self.errors} errors detected.'
        self.out += "```"
        await ctx.send(f'{self.out}')

    def absorbToken(self):
        self.value = ""
        if self.pointer >= len(self.code):
            self.token = "end of line"
            return
        while self.code[self.pointer] == " ":
            self.pointer += 1
        if self.pointer >= len(self.code):
            self.token = "eof"
        elif self.code[self.pointer] == "\\":
            self.token = "\\"
            self.value = "\\"
        elif self.code[self.pointer] == "(":
            self.token = "("
            self.value = "("
        elif self.code[self.pointer] == ")":
            self.token = ")"
            self.value = ")"
        elif self.code[self.pointer] == ".":
            self.token = "."
            self.value = "."
        else:
            self.token = "var"
            self.value += self.code[self.pointer]
            while self.pointer+1 < len(self.code) and self.code[self.pointer+1] not in ("\\", "(", ")", ".", " "):
                self.pointer += 1
                self.value += self.code[self.pointer]
        self.pointer += 1

    def absorbWithCheck(self, expectedTokens):
        if self.token not in expectedTokens:
            self.errors += 1
            if self.errors <= ERROR_LIMIT:
                self.printInvalidTokenError(expectedTokens)
        self.absorbToken()

    def printInvalidTokenError(self, expectedTokens):
        self.out += "Error: Expected " + (expectedTokens[0] if len(expectedTokens) == 1 else "one of " + str(expectedTokens)) + "\n"
        self.out += "  Found " + self.token + " at position " + str(self.pointer) + ":" + "\n"
        self.out += self.code + "\n"
        self.out += " "*(self.pointer-1) + "^" + "\n"

    def parseExpression(self):
        if self.token == "var":
            left = LambdaNodeVariable(self.value)
            self.absorbToken()  # Absorb variable
        elif self.token == "\\":
            self.absorbToken()  # Abosrb \
            varDec = self.value
            self.absorbWithCheck(("var",))  # Absorb variable declaration
            self.absorbWithCheck((".",))  # Absorb .
            child = self.parseExpression()
            left = LambdaNodeAbstraction(varDec, child)
        elif self.token == "(":
            self.absorbToken()  # Absorb (
            left = self.parseExpression()
            self.absorbWithCheck((")"),)  # Absorb )
        else:
            self.errors += 1
            if self.errors <= ERROR_LIMIT:
                self.printInvalidTokenError(("expression",))
            return
        while self.token in ("var", "\\", "("):
            if self.token == "var":
                right = LambdaNodeVariable(self.value)
                self.absorbToken()  # Absorb variable
            elif self.token == "\\":
                self.absorbToken()  # Abosrb \
                varDec = self.value
                self.absorbWithCheck(("var",))  # Absorb variable declaration
                self.absorbWithCheck((".",))  # Absorb .
                child = self.parseExpression()
                right = LambdaNodeAbstraction(varDec, child)
            elif self.token == "(":
                self.absorbToken()  # Absorb(
                right = self.parseExpression()
                self.absorbWithCheck((")",))  # Absorb )
            left = LambdaNodeApplication(left, right)
        return left

    def evaluate(self, code):
        self.pointer = 0
        self.token = ""
        self.value = ""
        self.error = False
        self.code = code.strip()
        if self.code == "":
            self.out += "Error: empty string"
            return
        self.absorbToken()
        e1 = self.parseExpression()
        if self.errors:
            return
        depth = 0
        e2 = e1.betaReduce()
        while not self.error and depth < DEPTH_LIMIT and str(e2) != str(e1):
            e1 = e2
            e2 = e1.betaReduce()
            depth += 1
        if depth == DEPTH_LIMIT:
            self.out += f'Warning: reduction limit reached ({DEPTH_LIMIT})\n'
        self.out += str(e2)
        return e2


class LambdaNodeVariable():
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def betaReduce(self):
        return self

    def replace(self, variable, replacement):
        if self.name == variable:
            return replacement.copy()
        return self

    def copy(self):
        return LambdaNodeVariable(self.name)


class LambdaNodeAbstraction():
    def __init__(self, variable, child):
        self.variable = variable
        self.child = child

    def __str__(self):
        return "(\\" + str(self.variable) + "." + str(self.child) + ")"

    def betaReduce(self):
        child = self.child.betaReduce()
        return LambdaNodeAbstraction(self.variable, child)

    def beginReplace(self, replacement):
        return self.child.replace(self.variable, replacement)

    def replace(self, variable, replacement):
        if self.variable != variable:
            child = self.child.replace(variable, replacement)
            return LambdaNodeAbstraction(self.variable, child)
        return self

    def copy(self):
        return LambdaNodeAbstraction(self.variable, self.child.copy())


class LambdaNodeApplication():
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return "(" + str(self.left) + " " + str(self.right) + ")"

    def betaReduce(self):
        if type(self.left) is LambdaNodeAbstraction:
            return self.left.beginReplace(self.right)
        left = self.left.betaReduce()
        right = self.right.betaReduce()
        return LambdaNodeApplication(left, right)

    def replace(self, variable, replacement):
        left = self.left.replace(variable, replacement)
        right = self.right.replace(variable, replacement)
        return LambdaNodeApplication(left, right)

    def copy(self):
        return LambdaNodeApplication(self.left.copy(), self.right.copy())


def setup(bot: Bot):
    bot.add_cog(Lcalc(bot))
