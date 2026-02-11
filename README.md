# LaserBase-Sketch
LaserBase Sketch

Photo-to-drawing reconstruction tool.
Creates clean line art by analyzing shapes instead of applying filters or tracing outlines.

The goal is not to preserve the photograph but to rebuild it as a readable drawing that can be engraved, printed or illustrated.

What it does

The program separates an image into two kinds of information:

Tone – surfaces and shading
Contour – edges and structure

Then rebuilds the image from these instead of editing pixels.

Result: a structured drawing, not a photo effect.

Why it is different

This is not

a filter

edge detection overlay

SVG tracer

background remover

The image is analyzed and redrawn based on forms.

Features

Photo → clean line drawing

Structure-based reconstruction

Adjustable detail level

Manual cleanup tools

Vector line reconstruction

Suitable for engraving and illustration

Vector reconstruction

Contours can be rebuilt as continuous paths.

This removes broken edges and noise and produces smoother lines.

Important for:

portraits (eyes, mouth)

buildings (straight lines)

logos (closed shapes)

Vector parameters affect structure, therefore they are applied as a rebuild step instead of live preview.

Usage

Open image

Choose drawing mode

Adjust detail and line strength

Optionally reconstruct lines

Export result

Download

Prebuilt executable is available in Releases.

No installation required.
Extract and run.

Notes

The quality of the original image strongly affects the result.
The program reconstructs structure — it cannot invent missing information.

License

This software is free to use but not open source.

You may use and download it.
You may not modify, redistribute modified versions, or sell it.

See LICENSE.txt for details.
