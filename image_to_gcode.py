import cv2
import numpy as np
import argparse


def generate_gcode(
    contours, output_path, power, feed_rate, scale_factor, offset_x=0, offset_y=0
):
    """
    Generate G-code from image contours.

    Args:
        contours (list): List of contours to generate G-code for.
        output_path (str): File path to save the G-code.
        power (int): Laser power setting.
        feed_rate (int): Feed rate (speed) for engraving.
        scale_factor (float): Scaling factor for the contours.
        offset_x (float): Offset in the X direction.
        offset_y (float): Offset in the Y direction.
    """
    with open(output_path, "w") as f:
        f.write("G21 ; Set units to millimeters\n")
        f.write("G90 ; Absolute positioning\n")
        f.write("M5 ; Ensure the laser is off to start\n")

        for contour in contours:
            for i, point in enumerate(contour):
                x, y = point[0]
                x = (x * scale_factor) + offset_x
                y = (y * scale_factor) + offset_y

                if i == 0:  # If it's the start of a contour
                    f.write(f"G0 X{x:.3f} Y{y:.3f}\n")
                    f.write(f"M3 S{power}\n")
                else:
                    f.write(f"G1 X{x:.3f} Y{y:.3f} F{feed_rate}\n")

            f.write("M5 ; Turn off the laser\n")

        # f.write("M5 ; Turn off the laser\n")
        f.write("G0 X0 Y0\n")

    print(f"G-code generated and saved to {output_path}")


def image_to_gcode(
    image_path,
    output_path,
    threshold,
    power,
    feed_rate,
    longest_side=None,
    center_offset=None,
):
    """
    Convert a PNG image to G-code for laser engraving.

    Args:
        image_path (str): The file path of the .png image to convert.
        output_path (str): The file path where to save the generated G-code.
        power (int): The power setting for the laser engraver.
        feed_rate (int): The feed rate for engraving.
        longest_side (float): Optional: The length of the longest side of the engraving in millimeters.
        center_offset (tuple): Optional: Center offset (X, Y) in millimeters.

    Returns:
        None: Writes the G-code to the specified output file.
    """
    # Load the image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    # Check if the image has been loaded correctly
    if img is None:
        raise ValueError("Image not found or the file format is not supported.")
    # Check if image has an alpha channel; if so, ignore it
    if img.shape[-1] == 4:
        img = img[:, :, :3]

    # Convert to grayscale
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply thresholding
    if threshold:
        _, binary = cv2.threshold(
            gray_img, threshold, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
    else:
        # Apply adaptive thresholding to the grayscale image
        binary = cv2.adaptiveThreshold(
            gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
    # flip for cutting
    binary = cv2.flip(binary, 0)
    # add a small amount of blur
    binary = cv2.GaussianBlur(binary, (1, 0), np.max(img.shape) * 0.0005)
    # Find the contours of the image
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Calculate scale factor and offsets
    scale_factor = 1
    if longest_side:
        current_longest_side_pixels = max(img.shape)
        scale_factor = longest_side / current_longest_side_pixels

    offset_x, offset_y = 0, 0
    if center_offset:
        offset_x, offset_y = center_offset

    generate_gcode(
        contours, output_path, power, feed_rate, scale_factor, offset_x, offset_y
    )


# Command line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a PNG image to G-code for laser engraving."
    )
    parser.add_argument(
        "image_path", help="The file path of the .png image to convert."
    )
    parser.add_argument(
        "output_path", help="The file path where to save the generated G-code."
    )
    parser.add_argument(
        "--power",
        type=int,
        default=1000,
        help="The power setting for the laser engraver.",
    )
    parser.add_argument(
        "--feed_rate", type=int, default=1000, help="The feed rate for engraving."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="The Thresholding level for the processing.",
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

    image_to_gcode(
        args.image_path,
        args.output_path,
        args.threshold,
        args.power,
        args.feed_rate,
        args.longest_side,
        args.center_offset,
    )
