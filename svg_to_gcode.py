from svgpathtools import svg2paths2, Line
import argparse
import re


def calculate_scaling_factor_and_transform(
    paths, svg_attributes, target_longest_side=None
):
    # Extract height from viewBox or height attribute
    if "viewBox" in svg_attributes:
        _, _, _, svg_height = map(float, svg_attributes["viewBox"].split())
    elif "height" in svg_attributes:
        svg_height = float(re.sub("[^0-9.-]", "", s_attr["height"]))
    else:
        raise ValueError(
            "SVG height not specified in 'viewBox' or 'height' attributes."
        )

    min_x, min_y, max_x, max_y = (
        float("inf"),
        float("inf"),
        float("-inf"),
        float("-inf"),
    )

    for path in paths:
        for line in path:
            min_x = min(min_x, line.start.real, line.end.real)
            max_x = max(max_x, line.start.real, line.end.real)
            min_y = min(min_y, line.start.imag, line.end.imag)
            max_y = max(max_y, line.start.imag, line.end.imag)

    # Flip vertically
    for path in paths:
        for line in path:
            line.start = complex(line.start.real, svg_height - line.start.imag)
            line.end = complex(line.end.real, svg_height - line.end.imag)

    current_longest_side = max(max_x - min_x, max_y - min_y)
    scale_factor = (
        1 if target_longest_side is None else target_longest_side / current_longest_side
    )

    return scale_factor, min_x, svg_height


def path_to_gcode(path, scale_factor, min_x, offset_x, offset_y, feed_rate, power):
    gcode = ""
    for segment in path:
        start_x = (segment.start.real - min_x) * scale_factor + offset_x
        start_y = (segment.start.imag) * scale_factor + offset_y
        end_x = (segment.end.real - min_x) * scale_factor + offset_x
        end_y = (segment.end.imag) * scale_factor + offset_y

        # Move to start of segment
        gcode += f"G0 X{start_x:.3f} Y{start_y:.3f}\n"
        gcode += f"M3 S{power}\n"  # Turn on the laser

        # Draw segment
        gcode += f"G1 X{end_x:.3f} Y{end_y:.3f} F{feed_rate}\n"
        gcode += "M5\n"  # Turn off the laser
    return gcode


def svg_to_gcode(
    svg_file,
    output_file,
    power,
    feed_rate,
    longest_side=None,
    center_offset=None,
):
    # Determine offset
    if center_offset:
        center_offset_x, center_offset_y = center_offset
    else:
        center_offset_x, center_offset_y = 0, 0

    paths, _, svg_attributes = svg2paths2(svg_file)
    scale_factor, min_x, svg_height = calculate_scaling_factor_and_transform(
        paths, svg_attributes, longest_side
    )

    # Calculate the center of the scaled bounding box
    scaled_width = (svg_height - min_x) * scale_factor
    scaled_height = svg_height * scale_factor
    center_x = min_x + scaled_width / 2
    center_y = scaled_height / 2

    # Adjusting the offset
    offset_x = center_offset_x - center_x
    offset_y = center_offset_y - center_y

    with open(output_file, "w") as f:
        f.write("G21 ; Set units to millimeters\n")
        f.write("G90 ; Absolute positioning\n")
        f.write("M5 ; Start with laser off\n")

        for path in paths:
            gcode_path = path_to_gcode(
                path, scale_factor, min_x, offset_x, offset_y, feed_rate, power
            )
            f.write(gcode_path)

        f.write("G0 X0 Y0\n")  # Return to home position

    print(f"G-code generated and saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert an SVG file to G-code for laser engraving."
    )
    parser.add_argument("svg_file", help="The SVG file path to convert.")
    parser.add_argument(
        "output_file", help="The file path to save the generated G-code."
    )
    parser.add_argument(
        "--power", type=int, default=1000, help="The laser power setting."
    )
    parser.add_argument(
        "--feed_rate", type=int, default=1000, help="The feed rate for engraving."
    )
    parser.add_argument(
        "--longest_side",
        type=float,
        default=None,
        help="Optional: The length of the longest side of the engraving in millimeters.",
    )
    parser.add_argument(
        "--center_offset",
        type=float,
        nargs=2,
        default=None,
        help="Optional: Center offset (X, Y) in millimeters to align the center of the scaled cut.",
    )

    args = parser.parse_args()

    svg_to_gcode(
        args.svg_file,
        args.output_file,
        args.power,
        args.feed_rate,
        args.longest_side,
        args.center_offset,
    )
