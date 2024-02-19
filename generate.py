import sys
from queue import Queue
from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())


    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            words = self.domains[var].copy()
            for word in words:
                if len(word) != var.length:
                    self.domains[var].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        overlap = self.crossword.overlaps[x,y]
        revised = False
        if overlap:
            revised = False
            words = self.domains[x].copy()
            for word in words:
                xLetter = word[overlap[0]]
                if not any(yword[overlap[1]] == xLetter for yword in self.domains[y]):
                    self.domains[x].remove(word)
                    revised = True
        
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not arcs:
            arcs = Queue()
            for overlap in self.crossword.overlaps:
                arcs.put(overlap)
        
        while not arcs.empty():
            (x, y) = arcs.get()
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                for z in self.crossword.neighbors(x):
                    arcs.put((z, x))
        return True
    
    def get_neighbors_overlap_queue(self, var):
        arcs = Queue()
        for overlap in self.crossword.overlaps:
            if overlap[1] == var:
                arcs.put(overlap)
        return arcs
    
    def make_domains_copy(self):
        domains_copy = {}
        for var in self.domains:
            domains_copy[var] = self.domains[var].copy()
        return domains_copy

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.domains:
            if not var in assignment:
                return False
            
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        used_words = set()
        assigned_words_count = 0
        for var in self.domains:
            if var in assignment and assignment[var]:
                used_words.add(assignment[var])
                assigned_words_count += 1
                neighbors = self.crossword.neighbors(var)
                for neighbor in neighbors:
                    if not neighbor in assignment or not assignment[neighbor]:
                        continue
                    overlap = self.crossword.overlaps[var, neighbor]
                    if assignment[var][overlap[0]] != assignment[neighbor][overlap[1]]:
                        return False
                if var.length != len(assignment[var]):
                    return False

        
        if len(used_words) != assigned_words_count:
            return False
        
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        word_scores = {}
        for word in self.domains[var]:
            word_scores[word] = 0
            for neighbor in self.crossword.neighbors(var):
                overlap = self.crossword.overlaps[var, neighbor]
                for neigbor_word in self.domains[neighbor]:
                    if neigbor_word in assignment:
                        continue
                    if word[overlap[0]] != neigbor_word[overlap[1]]:
                        word_scores[word] += 1
        return sorted(word_scores.keys(), key=lambda x: word_scores[x])

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        lowest_domain_count_variables = []
        lowest_domain_count = float('inf')
        for var in self.domains:
            if var in assignment:
                continue
            domain_count = len(self.domains[var])
            if domain_count < lowest_domain_count:
                lowest_domain_count = domain_count
                lowest_domain_count_variables = [var]
            elif domain_count == lowest_domain_count:
                lowest_domain_count_variables.append(var)

        highest_neighbors_count = float("-inf")
        for variable in lowest_domain_count_variables:
            neighbors_count = len(self.crossword.neighbors(variable))
            if highest_neighbors_count < neighbors_count:
                most_neighbors_variable = variable
                highest_neighbors_count = neighbors_count

        return most_neighbors_variable

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            assignment[var] = value
            if self.consistent(assignment):
                arcs_to_update = self.get_neighbors_overlap_queue(var)
                domains_before_consistencies = self.make_domains_copy()
                # print("\n\n*********\n\n")
                # print(assignment)
                # print("\n\n*********\n\n")
                # print(arcs_to_update)
                # print("\n\n*********\n\n")
                self.domains[var] = {value}
                if not self.ac3(arcs_to_update):
                    self.domains = domains_before_consistencies
                result = self.backtrack(assignment)
                if result:
                    return result
                else:
                    self.domains = domains_before_consistencies
            del assignment[var]

        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
