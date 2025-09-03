import turtle
import math

def draw_recursive_edge(t, length, depth):
    """
    Recursively draw an edge with geometric pattern modifications.

    Args:
        t: turtle object
        length: length of the current edge
        depth: current recursion depth
    """
    if depth == 0:
        # Base case: draw a straight line
        t.forward(length)
    else:
        # Divide edge into three equal segments
        segment_length = length / 3

        # Draw first segment
        draw_recursive_edge(t, segment_length, depth - 1)

        # Turn left 60 degrees and draw first side of equilateral triangle
        t.left(60)
        draw_recursive_edge(t, segment_length, depth - 1)

        # Turn right 120 degrees and draw second side of equilateral triangle
        t.right(120)
        draw_recursive_edge(t, segment_length, depth - 1)

        # Turn left 60 degrees to return to original direction
        t.left(60)

        # Draw the last segment
        draw_recursive_edge(t, segment_length, depth - 1)

def draw_geometric_pattern(num_sides, side_length, depth):
    """
    Draw a complete geometric pattern with the specified parameters.

    Args:
        num_sides: number of sides of the initial polygon
        side_length: length of each edge in pixels
        depth: recursion depth for pattern generation
    """
    # Set up the turtle
    t = turtle.Turtle()
    t.speed(0)  # Fastest speed
    t.pensize(2)

    # Calculate the angle for the polygon
    angle = 360 / num_sides

    # Draw the polygon with recursive edges
    for _ in range(num_sides):
        draw_recursive_edge(t, side_length, depth)
        t.right(angle)

    # Hide the turtle when done
    t.hideturtle()

def main():
    """
    Main function to get user input and generate the pattern.
    """
    print("Geometric Pattern Generator")
    print("=" * 30)

    # Get user input
    try:
        num_sides = int(input("Enter the number of sides: "))
        if num_sides < 3:
            print("Error: Number of sides must be at least 3")
            return

        side_length = float(input("Enter the side length: "))
        if side_length <= 0:
            print("Error: Side length must be positive")
            return

        depth = int(input("Enter the recursion depth: "))
        if depth < 0:
            print("Error: Recursion depth must be non-negative")
            return

    except ValueError:
        print("Error: Please enter valid numbers")
        return

    # Set up the screen
    screen = turtle.Screen()
    screen.title(f"Geometric Pattern - {num_sides} sides, depth {depth}")
    screen.bgcolor("white")

    # Calculate appropriate screen size based on pattern size
    # For complex patterns, we need more space
    pattern_size = side_length * (1.5 ** depth)  # Approximate size increase
    screen.setup(width=pattern_size * 2 + 100, height=pattern_size * 2 + 100)

    # Position turtle to center the pattern
    t = turtle.Turtle()
    t.penup()
    t.goto(-pattern_size/2, pattern_size/2)
    t.pendown()

    print(f"\nGenerating pattern with {num_sides} sides, length {side_length}, depth {depth}")
    print("Pattern generation complete! Close the window when done.")

    # Draw the pattern
    draw_geometric_pattern(num_sides, side_length, depth)

    # Keep the window open
    screen.mainloop()

if __name__ == "__main__":
    main()
