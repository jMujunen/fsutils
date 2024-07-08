"""Represents an image"""

import subprocess
import os
from datetime import datetime
from io import BytesIO
from typing import List

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
import ollama
import imagehash
import base64

from fsutils import File

# from .GenericFile import File
from size import Converter


class Img(File):
    """A class representing information about an image

    Attributes:
    ----------
        path (str): The absolute path to the file.

    Methods:
    ----------
        calculate_hash(self): Calculate the hash value of the image
        render(self, size=None): Render an image using kitty at a specified size (optional)
        generate_title(): EXPERIMENTAL! - Generate a title for the image using ollama
        resize(width=320, height=320) - Resize the image to a specified width and height

    Properties:
    ----------
        capture_date (str or None): Return the capture date of the image
        dimensions (tuple or None): Return a tuple containing the width and height of the image
        exif (dict or None): Return a dictionary containing EXIF data about the image if available
        is_corrupted (bool): Return True if the file is corrupted, False otherwise
    """

    def __init__(self, path: str):
        self._exif = None
        # self._capture_date = self._exif.
        super().__init__(path)

    def calculate_hash(self, spec: str = "avg") -> imagehash.ImageHash | None:
        """Calculate the hash value of the image

        Paramters:
        ---------
            spec (str): The specification for the hashing algorithm to use.

        Returns:
        ----------
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
                print(f"\033[1;31m{self.path} is corrupt\033[0m", end=f"{' '*80}\r", flush=True)

            print(f"Error calculating hash: {e}")

    @property
    def dimensions(self) -> tuple[int, int]:
        """
        Extract the dimensions of the image

        Returns:
        ----------
            Tuple(int, int): width x height of the image in pixels.
        """
        with Image.open(self.path) as img:
            width, height = img.size
        return width, height

    @property
    def exif(self) -> Image.Exif | None:
        """Extract the EXIF data from the image"""
        if self._exif is not None:
            return self._exif
        # Open Image
        try:
            with Image.open(self.path) as img:
                self._exif = img.getexif()
            return self._exif
        except UnidentifiedImageError as e:
            print(e)

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the image if it exists in the EXIF data."""
        # if self.exif is not None:
        #   tag, data = [(k, v) for k, v in self.exif.items() if isinstance(v, tuple)][0]
        # Iterating over all EXIF data fields
        if self.exif is None:
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
        date_str = str(datetime.fromtimestamp(os.path.getmtime(self.path))).split(".")[0]
        return datetime.fromisoformat(date_str)

    def generate_title(self) -> str | None:
        """Generate a title for the image using ollama"""
        try:
            response = ollama.chat(
                model="llava",
                messages=[
                    {
                        "role": "user",
                        "content": "Catagorize the image into 1 of the following based on the scene. Cat, Portrait, Car, Nature, Adventure",
                        "images": [self.path],
                    },
                ],
            )
            return response["message"]["content"]
        except Exception as e:
            print(f"An error occurred while generating a title:\n{str(e)}")

    def render(self, width: int = 640, height: int = 640):
        """Render the image in the terminal using kitty terminal"""
        try:
            subprocess.run(
                f'kitten icat --use-window-size {width},100,{height},100 "{self.path}"',
                shell=True,
                check=False,
            )
        except Exception as e:
            print(f"An error occurred while rendering the image:\n{str(e)}")

    def open(self) -> int:
        """Open the image in the OS default image viewer"""
        try:
            with Image.open(self.path) as f:
                f.show()
            return 0
        except UnidentifiedImageError as e:
            print(e)
        return 1

    def save(self, path):
        """Save the image to a specified location"""
        pass

    def resize(self, width: int = 320, height: int = 320, overwrite=False) -> str:
        """Resize the image to specified width and height

        Returns:
        ---------
            saved_image_path (str): Path to the new image
        """
        saved_image_path = os.path.join(self.dir_name, f"resized_{self.basename.strip('resized_')}")
        if (
            os.path.exists(saved_image_path)
            and not overwrite
            and Img(saved_image_path).dimensions == (width, height)
        ):
            return saved_image_path
        with Image.open(self.path) as img:
            resized_img = img.resize((width, height))
        try:
            resized_img.save(saved_image_path)
        except OSError as e:
            print(f"An error occurred while saving resized image:\n{str(e)}")
        finally:
            # buffered = BytesIO()
            # resized_img.save(buffered, format="JPEG")
            # img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return saved_image_path

    def compress(self, new_size_ratio=1, quality=90, width=None, height=None, to_jpg=False):
        """Compresses an image

        Paramaters:
        ---------
            new_size_ratio (float): The new size ratio of the image after compression
            quality (int): The quality of the compression from 0-100, where 100 is best quality and highest file size
            width (int): The new width of the image after resizing
            height (int): The new height of the image after resizing
            to_jpg (bool): Convert the image to jpg format if True, else keep it in its original format

        Returns:
        ---------
            str: The path to the compressed image file if successful, else an error message
            if an error occurred during saving the compressed image file to disk

        Raises:
        --------
            OSError: If an error occurred while saving the compressed image file to disk
            IOError: If an error occurred while opening the image file from disk
            ValueError: If an invalid value was passed for width, height or new_size_ratio parameters
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
                    (int(img.size[0] * new_size_ratio), int(img.size[1] * new_size_ratio))
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
                return f"Error while saving the compressed image.\n{e}"

            # get the new image size in bytes
            new_image_size = os.path.getsize(new_file_path)
            new_image_human = Converter(new_image_size)
            # print the new size in a good format
            print("\t[+] Size after compression:", (new_image_human))
            # calculate the saving bytes
            saving_diff = float(new_image_size) - self.size
            # print the saving percentage
            print(f"\t[+] Image size change: {
                saving_diff/self.size*100:.2f}% of the original image size.")
            print(f"{"="*60}")

    def to_base64(self) -> str:
        resized = self.resize()
        with Image.open(resized) as img:
            try:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                os.remove(resized)
            except OSError as e:
                print("OSError  while converting to base64:")
                return str(e)
        return img_str

    @property
    def is_corrupt(self) -> bool:
        """
        Check if the image is corrupt

        Returns:
        ----------
            bool: True if the image is corrupt, False otherwise
        """
        # If the file is a HEIC image, it cannot be verified
        if self.extension == ".heic":
            return False  # Placeholder TODO

        try:
            # Verify integrity of the image
            with Image.open(self.path) as f:
                f.verify()
            return False
        # If an IOError or SyntaxError is raised, the image is corrupt
        except (IOError, SyntaxError):
            return True
        except KeyboardInterrupt:
            return False
        # If any other exception is raised, we didnt account for something so print the error
        except Exception as e:
            print(f"Error: {e}")
            return False

    def __eq__(self, other) -> bool:
        return (
            True
            if super().__eq__(other) or self.calculate_hash() == other.calculate_hash()
            else False
        )


if __name__ == "__main__":
    img = Img("/tmp/pics/resized_os_crash.meme.jpg")
    print(img.dimensions)
    print(img.to_base64())
