"""Represents an image."""

import base64
import hashlib
import os
import subprocess
from datetime import datetime
from io import BytesIO

import cv2
import imagehash
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from size import Converter

from .GenericFile import File

ENCODE_SPEC = {".jpg": "JPEG", ".gif": "GIF", ".png": "JPEG"}


class Img(File):
    """A class representing information about an image

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

    def calculate_hash(self, spec: str = "avg") -> imagehash.ImageHash | None:
        """Calculate the hash value of the image

        Paramters:
        ---------
            spec (str): The specification for the hashing algorithm to use.

        Returns
        -------
            hash_table (array)  : The calculated hash of the image.
            None (None)         : NoneType if an error occurs while calculating the hash

        """
        specs = {
            "avg": lambda x: imagehash.average_hash(x),
            "dhash": lambda x: imagehash.dhash(x),
            "phash": lambda x: imagehash.phash(x),
        }
        # Ignore heic until feature is implemented to support it.
        # Excluding this has unwanted effects when comparing hash values
        if self.extension == ".heic":
            pass
        try:
            with Image.open(self.path) as img:
                hash_table = specs[spec](img)
            return hash_table
        except UnidentifiedImageError as e:
            file = Img(self.path)
            if file.is_corrupt:
                print(f"\033[1;31m{self.path} is corrupt\033[0m", end=f"{" " * 80}\r", flush=True)

            print(f"Error calculating hash: {e!r}")

    @property
    def dimensions(self) -> tuple[int, int]:
        """Extract the dimensions of the image

        Returns
        -------
            Tuple(int, int): width x height of the image in pixels.

        """
        with Image.open(self.path) as img:
            width, height = img.size
        return width, height

    @property
    def exif(self) -> Image.Exif | None:
        """Extract the EXIF data from the image"""
        if self._exif:
            return self._exif
        # Open Image
        try:
            with Image.open(self.path) as img:
                self._exif = img.getexif()
            return self._exif
        except UnidentifiedImageError as e:
            print(e)

    @property
    def tags(self):
        """Extract metadata from image files"""
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
                except:
                    continue
        else:
            self.__dict__.get("capture_date")
        date_str = str(datetime.fromtimestamp(os.path.getmtime(self.path))).split(".")[0]
        return datetime.fromisoformat(date_str)

    def render(self, render_size=320, title=True) -> int:
        """Render the image in the terminal using kitty graphics protocol

        Paramaters:
        ------------
        `render_size` int : The size of the image to render in terminal

        `title` : bool : If True, display the name with the image
        """
        try:
            if title:
                pos = round(
                    (render_size / 10) - (render_size % 360 / 10)
                )  # Vain attempt to center the title
                print(f"\033[1m{self.basename.center(pos)}\033[0m")
            return subprocess.run(
                f'kitten icat --use-window-size 100,100,{render_size},100 "{self.path}"',
                shell=True,
                check=False,
            ).returncode

        except Exception as e:
            print(f"An error occurred while rendering the image:\n{e!r}")
            return 1

    def open(self) -> int:
        """Open the image in the OS default image viewer"""
        try:
            with Image.open(self.path) as f:
                f.show()
            return 0
        except UnidentifiedImageError as e:
            print(e)
        return 1

    def save(self, path: str):
        """Save the image to a specified location"""
        raise NotImplementedError(self.__class__.__name__ + ".save() is not yet implemented.")

    def resize(
        self,
        width: int = 320,
        height: int = 320,
        overwrite=False,
        file_path: str | None = None,
    ) -> "Img":
        """Resize the image to specified width and height"""
        saved_image_path = os.path.join(self.dir_name, f"resized_{self.basename}")
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
        try:
            resized_img.save(saved_image_path)
        except OSError as e:
            print(f"An error occurred while saving resized image:\n{e!s}")
        return self.__class__(saved_image_path)

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
            - `new_size_ratio` (float): The new size ratio of the image after compression
            - `quality` (int): The quality of the compression from 0-100, where 100 is best quality and highest file size
            - `width` (int): The new width of the image after resizing
            - `height` (int): The new height of the image after resizing
            - `to_jpg` (bool): Convert the image to jpg format if True, else keep it in its original format

        Returns
        -------
            - `Img`: A new instance of the Img class with the compressed image path and dimensions

        Raises
        ------
            - `OSError` : If an error occurred while saving the compressed image file to disk
            - `IOError` : If an error occurred while opening the image file from disk
            - `ValueError` : If an invalid value was passed for width, height or new_size_ratio parameters

        """
        # load the image to memory
        with Image.open(self.path) as img:
            if to_jpg:
                # convert the image to RGB mode
                img = img.convert("RGB")

            # print the original image shape
            print(f"[*] Image shape: {img.size}")
            # print the size before compression/resizing
            print(f"[*] Size before compression:{Converter(self.size)}\n")

            if new_size_ratio < 1.0:
                # if resizing ratio is below 1.0, then multiply width & height with this ratio to reduce image size
                img = img.resize(
                    (int(img.size[0] * new_size_ratio), int(img.size[1] * new_size_ratio)),
                )
                # print new image shape
                print("\t[+] New Image shape:", img.size)
            elif width and height:
                # if width and height are set, resize with them instead
                img = img.resize((width, height))
                # print new image shape
                print("\t[+] New Image shape:", img.size)

            # make new filename appending _compressed to the original file name
            if to_jpg:
                # change the extension to JPEG
                new_filename = f"{self.basename}_compressed.jpg"
            else:
                # retain the same extension of the original image
                new_filename = f"{self.basename}_compressed{self.extension}"
            try:
                new_file_path = os.path.join(self.dir_name, new_filename)
                # save the image with the corresponding quality and optimize set to True
                img.save(new_file_path, quality=quality, optimize=True)
            except OSError as e:
                print(f"Error while saving the compressed image.\n{e!r}")

            # get the new image size in bytes
            new_image_size = os.path.getsize(new_file_path)
            new_image_human = Converter(new_image_size)
            # print the new size in a good format
            print("\t[+] Size after compression:", (new_image_human))
            # calculate the saving bytes
            saving_diff = float(new_image_size) - self.size
            # print the saving percentage
            print(f"\t[+] Image size change: {
                saving_diff / self.size * 100:.2f
            }% of the original image size.")
            print(f"{"=" * 60}")
            return self.__class__(new_file_path)

    def encode(self) -> str:
        """Base64 encode the image for LLM prococessing."""
        resized = self.resize()
        with Image.open(resized.path) as img:
            try:
                if self.extension == ".png":
                    # change the extension to JPEG
                    img = img.convert("RGB")
                buffered = BytesIO()
                img.save(buffered, format=ENCODE_SPEC.get(self.extension, "JPEG"))
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                os.remove(resized.path)
            except OSError as e:
                print(
                    f"OSError  while converting to base64: {self.extension}: spec=({ENCODE_SPEC.get(self.extension)})"
                )
                return str(e)
        return img_str

    def grayscale(self, output: str) -> "Img":
        """Convert the image to grayscale and save it to the specified output path."""
        img = cv2.imread(self.path)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(output, gray_img)
        return Img(output)

    def _read_chunk(self, size=8192) -> bytes:
        """Read a chunk of the file and return it as bytes."""
        with open(self.path, "rb") as f:
            return f.read(size)

    @property
    def md5_checksum(self, size=8192) -> str:
        """Return the MD5 checksum of a portion of the image file."""
        data = self._read_chunk(size)
        return hashlib.md5(data).hexdigest()

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
        # If any other exception is raised, we didnt account for something so print the error
        except Exception as e:
            print(f"Error: {e!r}")
            return False

    # def __eq__(self, other) -> bool:
    #     if not isinstance(other, self.__class__):
    #         return False
    #     return (
    #         True
    #         if super().__eq__(other) or self.calculate_hash() == other.calculate_hash()
    #         else False
    #     )
    def __eq__(self, other: "Img", /) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.md5_checksum, self.dimensions, self.size))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size_human}, path={self.path}, basename={self.basename}, extension={self.extension}, dimensions={self.dimensions}, capture_date={self.capture_date})".format(
            **vars(self),
        )
