"""Represents an image."""

import base64
import logging
import subprocess
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import exifread
import imagehash
import rawpy
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

from fsutils.utils.Exceptions import CorruptMediaError

exifread.logger.setLevel(logging.CRITICAL)

from fsutils.file import Base

ENCODE_SPEC = {".jpg": "JPEG", ".gif": "GIF", ".png": "JPEG"}

Dims = namedtuple("Dims", ["width", "height"])


class Img(Base):  # noqa: PLR0904
    """Represents an image.

    Methods
    -------
        - `calculate_hash(spec)` : Calculate the hash value of the image using a specified algorithm
        - `render()`             : Render the image in the terminal with a title for the image using ollama
        - `open()`                : Open the image in the OS default image viewer
        - `save(path)`            : Save the image to a specified location
        - `resize(height=480, tempfile=False, overwrite=False, **kwargs)`: Resize the image to specified size and mode.
        - `compress()`            : Compresses an image.
        - `encode()`              : Base64 encode the image.
        - `grayscale(output)`     : Convert the image to grayscale and save it to the specified output path.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize an Img object.

        Parameters
        ----------
            - `path (str)` : The absolute path to the file.
        """
        super().__init__(str(path))

    def find_sidecar(self) -> Base:
        """Search the current directory for a sidecar file and load its contents into the object."""
        return Base(f"{self.parent}/{self.name}.xmp")

    def calculate_hash(self, spec: str = "avg") -> imagehash.ImageHash:
        """Calculate the hash value of the image.

        Paramters:
        ---------
            spec : The specification for the hashing algorithm to use.
                            Supported values are 'avg', 'dhash', and 'phash'.

        Raises:
        -------
            ValueError : If the specified hashing algorithm is not supported.
        """
        # Ignore heic until feature is implemented to support it.
        # Excluding this has unwanted effects when comparing hash values
        if self.suffix == ".heic" or self.is_corrupt:
            pass
        with Image.open(self.path) as img:
            match spec:
                case "avg":
                    img_hash = imagehash.average_hash(img)
                case "dhash":
                    img_hash = imagehash.dhash(img)
                case "phash":
                    img_hash = imagehash.phash(img)
                case _:
                    raise ValueError("Invalid specification for hash algorithm")
        return img_hash

    @property
    def dimensions(self) -> tuple[int, int]:
        """Extract the dimensions of the image as a tuple."""
        with Image.open(self.path) as img:
            return img.size

    def tags(self, method="exifread") -> dict[str, Any]:
        """Return a list of all tags in the EXIF data."""

        def _exifread() -> dict[str, Any]:
            with open(self.path, "rb") as f:
                return {
                    tag: data
                    for tag, data in exifread.process_file(f).items()
                    if tag not in {"JPEGThumbnail", "TIFFThumbnail", "Filename"}
                }

        def _pilexif() -> dict[str, Any]:
            results = {}
            with Image.open(self.path) as f:
                exif = f.getexif()
            for tag_id in exif:
                tag = TAGS.get(tag_id, tag_id)
                data = exif.get(tag_id, "")
                if isinstance(data, bytes):
                    data = data.decode()
                elif isinstance(data, str):
                    data = data.replace("\x00", "")

                if tag == "XMLPacket":
                    continue  # Skip 'XMLPacket'
                if not data:
                    continue
                results[tag] = data
            return results

        if method == "pil":
            try:
                return _pilexif()
            except (UnidentifiedImageError, UnicodeDecodeError) as e:
                raise CorruptMediaError(self.path) from e
        try:
            return _exifread()
        except Exception:
            return _pilexif()

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the image if it exists in the EXIF data."""
        try:
            return datetime.fromisoformat(
                str(self.tags(method="pil")["DateTime"]).replace(":", "-", count=2)
            )
        except KeyError:
            return self.mtime

    def is_corrupt(self) -> bool:
        """Check if the image is corrupt."""
        # If the file is a HEIC image, it cannot be verified
        if self.suffix.lower() == ".heic":
            return False  # Placeholder TODO

        try:
            # Verify integrity of the image
            with Image.open(self.path) as f:
                f.verify()
            return False
        # If an IOError or SyntaxError is raised, the image is corrupt
        except (OSError, SyntaxError):
            return True
        except KeyboardInterrupt:
            return False
        # If any other exception is raised, we didn't account for something so print the error
        except Exception as e:
            print(f"Error: {e!r}")
            return False

    @property
    def aspect_ratio(self) -> float:
        """Calculate and return the aspect ratio of an image."""
        width, height = self.dimensions
        return round(width / height, 3)

    def render(self, render_size=320, show_title=True) -> int:
        """Render the image in a terminal window.

        Parameters
        -----------
            - `render_size (int)` : The size of the window in which to render the image.
            - `title (bool)` : Whether to display the title of the image in the terminal window.

        Returns
        -------
            int: The return code of the subprocess call. 0 if successful, non-zero otherwise.
        """
        try:
            if show_title:
                title = f"{self.name}\t{self.capture_date!s}"
                pos = round(
                    (render_size / 10) - (render_size % 360 / 10)
                )  # Vain attempt to center the title
                print(f"\033[1m{title.center(pos)}\033[0m")
            return subprocess.run(
                f'kitten icat --use-window-size 100,100,{render_size},100 "{self.path}"',
                shell=True,
                check=False,
            ).returncode

        except Exception as e:
            print(f"An error occurred while rendering the image:\n{e!r}")
            return 1

    def process_raw(self, output=None) -> "Img":
        """Process the raw file using rawpy and save it as a JPEG.

        Parameters
        ----------
            output : str, optional
                The path to save the processed JPEG file. If not provided, defaults to the current directory.

        Returns
        -------
            Img : The processed image and an instance of this class

        Raises
        ------
            ValueError : If the file is not a supported RAW file.
        """
        # Load presets if provided
        if output is None:
            # Default to the current directory with a .jpg extension
            output = Path(self.parent, f"{self.prefix}.jpg")
        preset_data = {"bright": 0.5, "use_camera_wb": False}
        if self.suffix.lower().endswith(".nef"):
            with rawpy.imread(self.path) as raw:
                rgb = raw.postprocess(**preset_data)
                image = Image.fromarray(rgb)
                image.save(output)
                return Img.__new__(Img, str(output))
        else:
            raise ValueError("Unsupported file format")

    def resize(self, width: int | None = None, height: int | None = None) -> "Img":
        """Resizes an image.

        Parameters
        ----------
            - `width (int)` : The new width of the image after resizing.
                If this parameter is not set, then the aspect ratio will be maintained while changing only the height to a new value.
            - `height (int)` : The new height of the image after resizing.
                If this parameter is not set, then the aspect ratio will be maintained while changing only the width to a new value.

        Returns
        -------
            Img: A new instance of the Img class with the resized image path and dimensions.

        Raises
        ------
            ValueError : If both `width` and `height` parameters are passed as `None`.
            OSError : If an error occurred while saving the resized image file to disk.
        """
        if not width and not height:
            raise ValueError("Both Width & Height cannot be none")

        # Make new filename prepending _resized to the original file name
        new_filename = f"_resized{self.name}"
        # Load the image to memory
        with Image.open(self.path) as img:
            # Unpack the tuple into two variables.
            match width, height:
                case None, None:
                    raise ValueError("Both Width & Height cannot be none")
                case None, _:
                    width = int(img.width * (height / img.height))
                case _, None:
                    height = int(img.height * (width / img.width))

            resized_img = img.resize((width, height))
            new_file_path = Path(self.parent, new_filename)
            resized_img.save(new_file_path)
            return self.__class__(new_file_path)

    def compress(
        self,
        new_size_ratio: float | int = 1.0,
        quality: int = 90,
        width: int | None = None,
        height: int | None = None,
        to_jpg=False,
    ) -> "Img":
        """Compresses an image.

        Paramaters:
        ---------
            - `new_size_ratio (float)`: The new size ratio of the image after compression
            - `quality (int)`: The quality of the compression from 0-100, where 100 is best quality and highest file size
            - `width (int)`: The new width of the image after resizing
            - `height (int)`: The new height of the image after resizing
            - `to_jpg (bool)`: Convert the image to jpg format if True, else keep it in its original format

        Returns
        -------
            - `Img`: A new instance of the Img class with the compressed image path and dimensions

        Raises
        ------
            - `OSError` : If an error occurred while saving the compressed image file to disk
            - `IOError` : If an error occurred while opening the image file from disk
            - `ValueError` : If an invalid value was passed for width, height or new_size_ratio parameters

        """
        if not isinstance(new_size_ratio, float | int) or new_size_ratio <= 0:
            raise ValueError("Invalid ratio provided.")

        # Create a temporary directory to store the compressed images
        tmp_dir = Path("/tmp/fsutils")
        tmp_dir.mkdir(exist_ok=True)

        filename_base = "_compressed" if not to_jpg else f"{self.name}_compressed.jpg"
        new_filename = Path.joinpath(tmp_dir, filename_base)

        with Image.open(self.path) as img:
            # Resize the image according to given dimensions or ratio
            if width and height:
                resized_img = img.resize((width, height))
            elif 0 < new_size_ratio < 1.0:
                resized_img = img.resize((
                    int(img.size[0] * new_size_ratio),
                    int(img.size[1] * new_size_ratio),
                ))
            else:
                raise ValueError("Invalid size parameters.")

            # Convert to RGB if converting to JPG
            if to_jpg:
                resized_img.convert("RGB")

            resized_img.save(new_filename, quality=quality, optimize=True)

        return self.__class__(new_filename)

    def encode(self) -> str:
        """Base64 encode the image."""
        # resized = self.resize()
        img = cv2.imread(self.path)
        cv_img = cv2.imencode(self.suffix, img)
        return base64.b64encode(cv_img[1]).decode("utf-8")

    def grayscale(self, output: str) -> "Img":
        """Convert the image to grayscale and save it to the specified output path."""
        img = cv2.imread(self.path)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(output, gray_img)
        return Img(output)

    def read(self) -> bytes:
        """Read the image and return its content as bytes."""
        return super()._read_chunk(4096)

    def __eq__(self, other: "Img", /) -> bool:
        return super().__eq__(other)

    def sha256(self, *args, **kwargs) -> str:
        return super().sha256(*args, **kwargs)

    def __hash__(self) -> int:
        return super().__hash__()

    def __format__(self, format_spec: str, /) -> str:
        """Return a formatted table representation of the file."""
        name = self.name
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[0]
            elif "_" in name:
                name = name.split("_")[0]
            else:
                name = name.split(" ")[0]
            iterations += 1
        return f"{name:<15} | {self.size_human:<10} | {self.dimensions!s:<15} | {self.capture_date!s:<25}"

    @staticmethod
    def fmtheader() -> str:
        """Return a formatted table header."""
        template = "{:<15} | {:<10} | {:<15} |{:<25}"
        header = template.format("File", "Ext", "Size", "Dimensions", "Capture Date")
        linebreak = template.format("-" * 15, "-" * 10, "-" * 15, "-" * 25)
        return f"\033[1m{header}\033[0m\n{linebreak}"  # type: ignore

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human}, dimensions={self.dimensions})"
