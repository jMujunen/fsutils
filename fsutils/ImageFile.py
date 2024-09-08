"""Represents an image."""

import base64
import os
import subprocess
from collections.abc import Generator
from datetime import datetime
from io import BytesIO
from typing import Never

import chardet
import cv2
import imagehash
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

from .GenericFile import File

ENCODE_SPEC = {".jpg": "JPEG", ".gif": "GIF", ".png": "JPEG"}


class Img(File):
    """A class representing information about an image.

    Attributes
    ----------
        - `path (str)` : The absolute path to the file.

    Methods
    -------
        - `calculate_hash(self)` : Calculate the hash value of the image
        - `render(self, size=None`): Render an image using kitty at a specified size (optional)
        - `generate_title()` : EXPERIMENTAL! - Generate a title for the image using ollama
        - `resize(width=320, height=320)` : Resize the image to a specified width and height

    Properties:
    ----------
        - `capture_date` (str) : Return the capture date of the image
        - `dimensions` (tuple) : Return a tuple containing the width and height of the image
        - `exif` (dict)        : Return a dictionary containing EXIF data about the image if available
        - `is_corrupted` (bool): Return True if the file is corrupted, False otherwise
    """

    def __init__(self, path: str) -> None:
        self._exif: Image.Exif = Image.Exif()
        self._tags = []
        super().__init__(path)

    def calculate_hash(self, spec: str = "avg") -> imagehash.ImageHash:
        """Calculate the hash value of the image.

        Paramters:
        ---------
            - `spec (str)` : The specification for the hashing algorithm to use.

        """
        # Ignore heic until feature is implemented to support it.
        # Excluding this has unwanted effects when comparing hash values
        if self.extension == ".heic" or self.is_corrupt:
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
        """Extract the dimensions of the image.

        Returns
        -------
            - `Tuple(int, int)` : width x height of the image in pixels.

        """
        with Image.open(self.path) as img:
            width, height = img.size
        return width, height

    @property
    def exif(self) -> Image.Exif | None:
        """Extract the EXIF data from the image."""
        if self._exif:
            return self._exif
        # Open Image
        try:
            with Image.open(self.path) as img:
                self._exif = img.getexif()
            return self._exif
        except UnidentifiedImageError as e:
            print(f"{e!r}")

    @property
    def tags(self) -> Generator | None:
        """Extract metadata from image files."""
        for tag_id in self.exif:
            try:
                tags = TAGS.get(tag_id, tag_id)
                data = self.exif.get(tag_id)
                if isinstance(data, bytes):
                    data = data.decode()
                if tags == "XMLPacket":
                    continue  # Skip 'XMLPacket'
                tag = (tags, data)
                if tag not in self._tags:
                    self._tags.append(tag)
                yield tag
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error extracting tag {tag_id}: {e!r}")
                continue

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the image if it exists in the EXIF data."""
        # if self.exif is not None:
        #   tag, data = [(k, v) for k, v in self.exif.items() if isinstance(v, tuple)][0]
        # Iterating over all EXIF data fields
        if self._exif is None:
            for tag_id in self.exif:
                try:
                    # Get the tag name, instead of human unreadable tag id
                    tag = TAGS.get(tag_id, tag_id)
                    data = self.exif.get(tag_id)
                    # Decode bytes
                    if isinstance(data, bytes):
                        data = data.decode()
                    if str(tag).startswith("DateTime"):
                        date, time = str(data).split(" ")
                        year, month, day = date.split(":")
                        hour, minute, second = time.split(":")
                        return datetime(
                            int(year),
                            int(month),
                            int(day),
                            int(hour),
                            int(minute),
                            int(second[:2]),
                        )
                except:  # noqa
                    continue
        else:
            self.__dict__.get("capture_date")
        date_str = str(datetime.fromtimestamp(os.path.getmtime(self.path))).split(".")[0]
        return datetime.fromisoformat(date_str)

    @property
    def is_corrupt(self) -> bool:
        """Check if the image is corrupt."""
        # If the file is a HEIC image, it cannot be verified
        if self.extension == ".heic":
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

    @staticmethod
    def show(path: str, render_size=320, title=True) -> int:
        """`HACK`: Mirror of render()."""
        if title:
            title = f"{os.path.split(path)[-1]}"
            pos = round(
                (render_size / 10) - (render_size % 360 / 10)
            )  # Vain attempt to center the title
            print(f"\033[1m{title.center(pos)}\033[0m")
        return subprocess.run(
            f'kitten icat --use-window-size 100,100,320,100 "{path}"',
            shell=True,
            check=False,
        ).returncode

    def render(self, render_size=320, title=True) -> int:
        try:
            if title:
                title = f"{self.filename}\t{self.capture_date!s}"
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

    def open(self) -> None:
        """Open the image in the OS default image viewer."""
        with Image.open(self.path) as f:
            f.show()

    def save(self, path: str) -> Never:
        """Save the image to a specified location."""
        raise NotImplementedError(self.__class__.__name__ + ".save() is not yet implemented.")

    def resize(
        self,
        width: int = 320,
        height: int = 320,
        overwrite=False,
        file_path: str | None = None,
    ) -> "Img":
        """Resize the image to specified width and height."""
        saved_image_path = os.path.join(self.dir_name, f"_resized-{self.filename}")
        if file_path is not None:
            saved_image_path = file_path
        if (
            os.path.exists(saved_image_path)
            and not overwrite
            and Img(saved_image_path).dimensions == (width, height)
        ):
            return self.__class__(saved_image_path)
        with Image.open(self.path) as img:
            resized_img = img.resize((width, height))
            resized_img.save(saved_image_path)
            return self.__class__(saved_image_path)

    def compress(
        self,
        new_size_ratio: float | int = 1.0,
        quality: int = 90,
        width: int | None = None,
        height: int | None = None,
        to_jpg=False,
    ) -> "Img | None":
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

        """
        # Make new filename prepending _compressed to the original file name
        new_filename = f"_compressed{self.filename}"
        # Load the image to memory
        with Image.open(self.path) as img:
            if to_jpg:
                # convert the image to RGB mode
                img.convert("RGB")
                new_filename = f"{self.filename}_compressed.jpg"
            # Multiply width & height with `ratio`` to reduce image size
            if new_size_ratio < 1.0:
                img.resize(
                    (int(img.size[0] * new_size_ratio), int(img.size[1] * new_size_ratio)),
                )
            elif width and height:
                img.resize((width, height))
            try:
                new_file_path = os.path.join(self.dir_name, new_filename)
                img.save(new_file_path, quality=quality, optimize=True)
                resized_img = self.__class__(new_file_path)
            except (OSError, PermissionError):
                print("Permission Denied")
                return None
            except Exception as e:
                print(f"Error: {e:!r}")
                return None
        # Calculate file size reduction
        size_diff = (resized_img.size - self.size) / self.size * 100
        print(f"The image was reduced by {size_diff:.2f}%.")
        return resized_img

    def detect_encoding(self) -> str | None:
        """Detect the encoding of a file.

        Returns:
            str: The detected encoding.
        Raises:
            Exception: If an error occurs while reading the file or detecting its encoding.
        """
        with open(self.path, "rb") as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        return result["encoding"]

    def encode(self) -> str:
        """Base64 encode the image."""
        resized = self.resize()
        with Image.open(resized.path) as img:
            try:
                if self.extension == ".png":
                    # change the extension to JPEG
                    img.convert("RGB")
                buffered = BytesIO()
                img.save(buffered, format=ENCODE_SPEC.get(self.extension, "JPEG"))
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                os.remove(resized.path)
            except OSError as e:
                print(
                    f"OSError  while converting to base64: {self.extension}: spec=({ENCODE_SPEC.get(self.extension)})"
                )
                return format(e, "r")
        return img_str

    def grayscale(self, output: str) -> "Img":
        """Convert the image to grayscale and save it to the specified output path."""
        img = cv2.imread(self.path)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(output, gray_img)
        return Img(output)

    def __eq__(self, other: "Img", /) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.md5_checksum, self.dimensions, self.size))

    def __format__(self, format_spec: str, /) -> str:
        """Return a formatted table representation of the file."""
        name = self.filename
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[0]
            elif "_" in name:
                name = name.split("_")[0]
            else:
                name = name.split(" ")[0]
            iterations += 1
        return f"{name:<25} | {self.extension:<6} | {self.size_human:<10} | {self.dimensions!s:<15} | {self.capture_date!s:<25}"

    @staticmethod
    def fmtheader() -> str:
        """Return a formatted table header."""
        template = "{:<25} | {:<6} | {:<10} | {:<15} |{:<25}"
        header = template.format("File", "Ext", "Size", "Dimensions", "Capture Date")
        linebreak = template.format("-" * 25, "-" * 6, "-" * 10, "-" * 15, "-" * 25)
        return f"\033[1m{header}\033[0m\n{linebreak}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size_human}, path={self.path}, basename={self.filename}, extension={self.extension}, dimensions={self.dimensions}, capture_date={self.capture_date})".format(
            **vars(self),
        )
