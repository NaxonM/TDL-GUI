from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class ExprSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Numeric literals
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#6897BB"))
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+\b"), number_format))

        # String literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#6A8759"))
        self.highlighting_rules.append((QRegularExpression(r"'.*?'"), string_format))
        self.highlighting_rules.append((QRegularExpression(r'".*?"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r"`.*?`"), string_format))

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#CC7832"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "let", "in", "and", "or", "not", "matches", "true", "false", "nil"
        ]
        for word in keywords:
            self.highlighting_rules.append(
                (QRegularExpression(rf"\b{word}\b"), keyword_format)
            )

        # Built-in functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#FFC66D"))
        functions = [
            "trim", "trimPrefix", "trimSuffix", "upper", "lower", "split",
            "splitAfter", "replace", "repeat", "indexOf", "lastIndexOf",
            "hasPrefix", "hasSuffix", "now", "duration", "date", "timezone",
            "max", "min", "abs", "ceil", "floor", "round", "all", "any", "one",
            "none", "map", "filter", "find", "findIndex", "findLast",
            "findLastIndex", "groupBy", "count", "concat", "flatten", "uniq",
            "join", "reduce", "sum", "mean", "median", "first", "last", "take",
            "reverse", "sort", "sortBy", "keys", "values", "type", "int",
            "float", "string", "toJSON", "fromJSON", "toBase64", "fromBase64",
            "toPairs", "fromPairs", "len", "get", "bitand", "bitor", "bitxor",
            "bitnand", "bitnot", "bitshl", "bitshr", "bitushr"
        ]
        for word in functions:
            self.highlighting_rules.append(
                (QRegularExpression(rf"\b{word}\b"), function_format)
            )

        # Built-in variables
        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor("#9876AA"))
        variables = ["Message", "From"]
        for word in variables:
            self.highlighting_rules.append(
                (QRegularExpression(rf"\b{word}\b"), variable_format)
            )

        # Operators
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#A9B7C6"))
        operators = [
            r"\+", r"-", r"\*", r"/", r"%", r"\^", r"\*\*", r"==", r"!=", r"<",
            r">", r"<=", r">=", r"&&", r"\|\|", r"!", r"\?:", r"\?\?", r"\|"
        ]
        for op in operators:
            self.highlighting_rules.append(
                (QRegularExpression(op), operator_format)
            )

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegularExpression(r"//[^\n]*"), comment_format))
        self.multi_line_comment_format = QTextCharFormat()
        self.multi_line_comment_format.setForeground(QColor("#808080"))
        self.multi_line_comment_format.setFontItalic(True)
        self.comment_start_expression = QRegularExpression(r"/\*")
        self.comment_end_expression = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        # First, apply all single-line rules
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Then, handle multi-line comments, which can span across blocks
        self.setCurrentBlockState(0)
        current_pos = 0

        # Check if the previous block was in a comment state
        if self.previousBlockState() == 1:
            # Search for the end of the comment from the beginning of the current block
            end_match = self.comment_end_expression.match(text, 0)
            if not end_match.hasMatch():
                # Comment doesn't end in this block, so highlight the whole block
                self.setCurrentBlockState(1)
                self.setFormat(0, len(text), self.multi_line_comment_format)
                return  # Stop further processing for this block
            else:
                # Comment ends here
                end_index = end_match.capturedEnd()
                self.setFormat(0, end_index, self.multi_line_comment_format)
                current_pos = end_index

        # Search for all occurrences of the start of a comment in the current block
        while True:
            start_match = self.comment_start_expression.match(text, current_pos)
            if not start_match.hasMatch():
                break  # No more comment starts found

            start_index = start_match.capturedStart()

            # Now, search for the end of the comment
            end_match = self.comment_end_expression.match(text, start_match.capturedEnd())

            if not end_match.hasMatch():
                # Comment starts but doesn't end in this block
                self.setCurrentBlockState(1)
                self.setFormat(start_index, len(text) - start_index, self.multi_line_comment_format)
                break  # Stop further processing for this block
            else:
                # Comment starts and ends within this block
                end_index = end_match.capturedEnd()
                length = end_index - start_index
                self.setFormat(start_index, length, self.multi_line_comment_format)
                current_pos = end_index
