#!/usr/bin/env python3

# MetaData.py - This module contains reusable file objects. Most of the mutable state is metadata

import os
import sys
import re
import json
import subprocess

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from moviepy.editor import VideoFileClip
import cv2

import imagehash

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")

FILE_TYPES = {
    "img": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".heic",
        ".nef",
    ],
    "img_other": [".heatmap", ".ico", ".svg", ".webp"],
    "metadata": [".xml", "aae", "exif", "iptc", "tiff", "xmp"],
    "doc": [".pdf", ".doc", ".docx", ".txt", ".odt", ".pptx"],
    "video": [".mp4", ".avi", ".mkv", ".wmv", ".webm", ".m4v", ".flv", ".mpg", ".mov"],
    "audio": [
        ".3ga",
        ".aac",
        ".ac3",
        ".aif",
        ".aiff",
        ".alac",
        ".amr",
        ".ape",
        ".au",
        ".dss",
        ".flac",
        ".flv",
        ".m4a",
        ".m4b",
        ".m4p",
        ".mp3",
        ".mpga",
        ".ogg",
        ".oga",
        ".mogg",
        ".opus",
        ".qcp",
        ".tta",
        ".voc",
        ".wav",
        ".wma",
        ".wv",
    ],
    "zip": [
        ".zip",
        ".rar",
        ".tar",
        ".bz2",
        ".7z",
        ".gz",
        ".xz",
        ".tar.gz",
        ".tgz",
        ".zipx",
    ],
    "raw": [".cr2", ".nef", ".raf", ".dng", ".raf"],
    "settings": [".properties", "ini", ".config", ".cfg", ".conf", ".yml", ".yaml"],
    "text": [".txt", ".md", ".log", ".json", ".csv", ".out", ".note"],
    "code": [
        ".py",
        ".bat",
        ".sh",
        ".c",
        ".cpp",
        ".h",
        ".java",
        ".js",
        ".ts",
        ".php",
        ".html",
        ".css",
        ".scss",
        ".ps1",
    ],
    "other": [
        ".lrprev",
        ".dat",
        ".db",
        ".dbf",
        ".mdb",
        ".sqlite",
        ".sqlite3",
        ".exe",
        ".mdat",
        ".thp",
        ".jar",
        ".mca",
        ".dll",
        ".package",
    ],  # For any other file type
    "ignored": [
        ".trashinfo",
        ".lnk",
        ".plist",
        ".shadow",
        "directoryStoreFile",
        "indexArrays",
        "indexBigDates",
        "indexCompactDirectory",
        "indexDirectory",
        "indexGroups",
        "indexHead",
        "indexIds",
        "indexPositions",
        "indexPostings",
        "indexUpdates",
        "shadowIndexGroups",
        "shadowIndexHead",
        "indexPositionTable",
        "indexTermIds",
        "shadowIndexArrays",
        "shadowIndexCompactDirectory",
        "shadowIndexDirectory",
        "shadowIndexTermIds",
        ".updates",
        ".loc",
        ".state",
        ".37",
        ".tmp",
        ".pyc",
        ".cachedmsg",
        ".git",
    ],
    "dupes": [],  # For duplicate files
}


class FileObject:
    """
    This is the base class for all of the following objects. 
    It represents a generic file and defines the common methods that are used by all of them.
    It can be used standlone (Eg. text based files) or as a parent class for other classes.
    
    Attributes:
    ----------
        encoding (str): The encoding to use when reading/writing the file. Defaults to utf-8.
        path (str): The absolute path to the file.
        content (Any): Contains the content of the file. Only holds a value if read() is called.

    Properties:
    ----------
        size: The size of the file in bytes.
        file_name: The name of the file without its extension.
        extension: The extension of the file (Eg. file.out.txt -> file.out)
        basename: The basename of the file (Eg. file.out.txt)
        is_file: Check if the objects path is a file
        is_executable: Check if the object has an executable flag
        is_image: Check if item is an image
        is_video: Check if item is a video
        is_gitobject: Check if item is a git object
        content: The content of the file. Only holds a value if read() is called.

    Methods:
    ----------
        read(): Return the contents of the file
        head(self, n=5): Return the first n lines of the file
        tail(self, n=5): Return the last n lines of the file
        __eq__(): Compare properties of FileObjects
        __str__(): Return a string representation of the object
        
    """
    def __init__(self, path, encoding='utf-8'):
        """
        Constructor for the FileObject class.

        Paramaters:
        ----------
            path (str): The path to the file
            encoding (str): Encoding type of the file (default is utf-8)
        """
        self.encoding = encoding
        self.path = path
        self._content = None

    def head(self, n=5):
        """
        Return the first n lines of the file

        Paramaters:
        ----------
            n (int): The number of lines to return (default is 5)

        Returns:
        ----------
            str: The first n lines of the file
        """
        lines = []
        if isinstance(self, (FileObject, ExecutableObject)):
            with open(self.path, 'r', encoding = self.encoding) as f:
                lines = [next(f) for _ in range(n)]
        return ''.join(lines)

    def tail(self, n=5):
        """
        Return the last n lines of the file

        Paramaters:
        ----------
            n (int): The number of lines to return (default is 5)

        Returns:
        ----------
            str: The last n lines of the file
        """
        lines = []
        if isinstance(self, (FileObject, ExecutableObject)):
            with open(self.path, 'r', encoding = self.encoding) as f:
                lines = f.readlines()[-n:]
        return ''.join(lines)

    @property
    def size(self):
        """
        Return the size of the file in bytes

        Returns:
        ----------
            int: The size of the file in bytes
        """
        return int(os.path.getsize(self.path))
    @property
    def dir_name(self):
        """
        Return the parent directory of the file

        Returns:
            str: The parent directory of the file
        """
        return os.path.dirname(self.path) if not self.is_dir else self.path
    @property
    def file_name(self):
        """
        Return the file name without the extension

        Returns:
        ----------
            str: The file name without the extension
        """
        return str(os.path.splitext(self.path)[0])

    @property
    def basename(self):
        """
        Return the file name with the extension

        Returns:
        ----------
            str: The file name with the extension
        """
        return str(os.path.basename(self.path))

    @property
    def extension(self):
        """
        Return the file extension

        Returns:
        ----------
            str: The file extension
        """
        return str(os.path.splitext(self.path)[-1]).lower()
    @property
    def content(self):
        if not self._content:
            self._content = self.read()
        return self._content
    def read(self):
        """
        Method for reading the content of a file. This method should overridden for VideoObjects

        Returns:
        ----------
            str: The content of the file
        """
        if isinstance(self, ImageObject):
            with open(self.path, "rb") as f:
                content = f.read()
        elif isinstance(self, (FileObject, ExecutableObject)):
            with open(self.path, "r", encoding=self.encoding) as f:
                content = f.read()
        try:
            content = content.decode()
        except (UnicodeDecodeError, AttributeError):
            content = content
        finally:
            return content

    @property
    def is_file(self):
        """
        Check if the object is a file

        Returns:
        ----------
            bool: True if the object is a file, False otherwise
        """
        if GIT_OBJECT_REGEX.match(self.basename):
            return False
        return os.path.isfile(self.path)

    @property
    def is_executable(self):
        """
        Check if the file is executable

        Returns:
        ----------
            bool: True if the file is executable, False otherwise
        """
        return os.access(self.path, os.X_OK)

    @property
    def is_dir(self):
        """
        Check if the object is a directory

        Returns:
        ----------
            bool: True if the object is a directory, False otherwise
        """
        return os.path.isdir(self.path)

    @property
    def is_video(self):
        """
        Check if the file is a video

        Returns:
        ----------
            bool: True if the file is a video, False otherwise
        """
        return self.extension.lower() in FILE_TYPES["video"]

    @property
    def is_gitobject(self):
        """
        Check if the file is a git object

        Returns:
        ----------
            bool: True if the file is a git object, False otherwise
        """
        return GIT_OBJECT_REGEX.match(self.basename)

    @property
    def is_image(self):
        """
        Check if the file is an image

        Returns:
        ----------
            bool: True if the file is an image, False otherwise
        """
        return self.extension.lower() in FILE_TYPES["img"]

    def __eq__(self, other):
        """
        Compare two FileObjects

        Paramaters:
        ----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        Returns:
        ----------
            bool: True if the two Objects are equal, False otherwise
        """
        if not isinstance(other, FileObject):
            return False
        elif isinstance(other, VideoObject):
            return self.size == other.size
        elif not self._content:
            self._content = self.read()
        return self._content == other.content

    def __str__(self):
        """
        Return a string representation of the FileObject

        Returns:
        ----------
            str: A string representation of the FileObject
        """
        return str(self.__dict__)

class ExecutableObject(FileObject):
    """
    A class representing information about an executable file
    
    Attributes:
    ----------
        path (str): The absolute path to the file. (Required)

    Properties:
    ----------
        shebang (str): Return the shebang line of the file
        shebang.setter (str): Set a new shebang
    """
    def __init__(self, path):
        self._shebang = None
        super().__init__(path)

    @property
    def shebang(self):
        """
        Get the shebang line of the file.

        Returns:
        ----------
            str: The shebang line of the file
        """
        if self._shebang is None:
            self._shebang = self.head(1).strip()
        return self._shebang

    @shebang.setter
    def shebang(self, shebang):
        """
        Set a new shebang line for the file.

        Paramaters:
        ----------
            shebang (str): The new shebang line

        Returns:
        ----------
            str: The content of the file after updating the shebang line
        """
        self._content = shebang + self.read()[len(self.shebang.strip()) :]
        try:
            with open(self.path, "w") as f:
                f.seek(0)
                f.write(self._content)

            print(f"{self.basename}\n{self.shebang} -> {shebang}")
            print(self.tail(2))
            self._shebang = shebang
            return self._content
        except PermissionError:
            print(f"Permission denied: {self.path}")
            pass


class DirectoryObject(FileObject):
    """
    A class representing information about a directory.
    
    Attributes:
    ----------
        path (str): The path to the directory (Required)
        _files (list): A list of file names in the directory
        _directories (list): A list containing the paths of subdirectories
        _objects (list): A list of items in the directory represented by FileObject
    
    Methods:
    ----------
        file_info (file_name): Returns information about a specific file in the directory
        objects (): Convert each file in self to an appropriate type of object inheriting from FileObject
        __eq__ (other): Compare properties of two DirectoryObjects
        __contains__ (other): Check if an item is present in two DirectoryObjects
        __len__ (): Return the number of items in the object
        __iter__ (): Define an iterator which yields the appropriate instance of FileObject
    
    Properties:
    ----------
        files       : A read-only property returning a list of file names
        objects     : A read-only property yielding a sequence of DirectoryObject or FileObject instances
        directories : A read-only property yielding a list of absolute paths for subdirectories
    
    """
    def __init__(self, path):
        self.path = path
        self._files = None
        self._directories = None
        self._objects = None
        super().__init__(self.path)

    @property
    def files(self):
        """
        Return a list of file names in the directory represented by this object.

        Returns:
        ----------
            list: A list of file names
        """
        if self._files is None:
            self._files = [file for folder in os.walk(self.path) for file in folder[2]]
        return self._files
    @property
    def directories(self):
        """
        Return a list of subdirectory paths in the directory represented by this object.

        Returns:
        ----------
            list: A list of subdirectory paths
        """
        if self._directories is None:
            self._directories = [folder[0] for folder in os.walk(self.path)]
        return self._directories
    @property
    def rel_directories(self):
        """
        Return a list of subdirectory paths relative to the directory represented by this object

        Returns:
            list: A list of subdirectory paths relative to the directory represented by this object
        """
        return [folder.replace(self.path, "") for folder in self.directories]

    def objects(self):
        """
        Convert each file in self to an appropriate type of object inheriting from FileObject.

        Returns:
        ------
            The appropriate inhearitance of FileObject
        """
        if self._objects is None:
            self._objects = [item for item in self]
        return self._objects
        
    def file_info(self, file_name):
        """
        Query the object for files with the given name. Returns an appropriate FileObject if found.

        Paramaters
        ----------
            file_name (str): The name of the file
        Returns:
        ---------

            FileObject: Information about the specified file
        """
        if file_name not in self.files:
            return
        
        # if len(self.directories) == 0:
        #     for f in os.listdir(self.path):
        #         if f == file_name:
        #             return FileObject(os.path.join(self.path, f))
        try:
            try:
                if file_name in os.listdir(self.path):
                    return obj(os.path.join(self.path, file_name))
            except NotADirectoryError:
                pass
            for d in self.directories:
                if file_name in os.listdir(os.path.join(self.path, d)):
                    return obj(os.path.join(self.path, d, file_name))
        except (FileNotFoundError, NotADirectoryError) as e:
            print(e)
            pass
    @property
    def images(self):
        """
        Return a list of ImageObject instances found in the directory.
        
        Returns:
        --------
            List[ImageObject]: A list of ImageObject instances
        """
        return [item for item in self if isinstance(item, ImageObject)]
    def videos(self):
        """
        Return a list of VideoObject instances found in the directory.
        
        Returns:
            List[VideoObject]: A list of VideoObject instances
        """
        return [item for item in self if isinstance(item, VideoObject)]
    @property
    def dirs(self):
        """
        Return a list of DirectoryObject instances found in the directory.
        
        Returns:
            List[DirectoryObject]: A list of DirectoryObject instances
        """
        return [item for item in self if isinstance(item, DirectoryObject)]
    
    def __contains__(self, item):
        """
        Compare items in two DirecoryObjects

        Parameters:
        ----------
            item (FileObject, VideoObject, ImageObject, ExecutableObject, DirectoryObject): The item to check.

        Returns:
        ----------
            bool: True if the item is present, False otherwise.
        """
        if (
            isinstance(item, FileObject)
            or isinstance(item, VideoObject)
            or isinstance(item, ImageObject)
            or isinstance(item, ExecutableObject)
            or isinstance(item, DirectoryObject)
        ):
            return item.basename in self.files
        return item in self.files

    def __len__(self):
        """
        Return the number of items in the object
        
        Returns:
        ----------
            int: The number of files and subdirectories in the directory
        """
        return len(self.directories) + len(self.files)

    def __iter__(self):
        """
        Yield a sequence of FileObject instances for each item in self
        
        Yields:
        -------
            FileObject: The appropriate instance of FileObject
        """
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if os.path.splitext(file)[1].lower() in FILE_TYPES["video"]:
                    yield VideoObject(os.path.join(root, file))
                elif os.path.splitext(file)[1].lower() in FILE_TYPES["img"]:
                    yield ImageObject(os.path.join(root, file))
                elif os.path.splitext(file)[1].lower() in FILE_TYPES["code"]:
                    yield ExecutableObject(os.path.join(root, file))
                else:
                    yield FileObject(os.path.join(root, file))
            for directory in dirs:
                yield DirectoryObject(os.path.join(self.path, directory))
    def __eq__(self, other):
        """
        Compare two DirectoryObjects

        Parameters:
        ----------
            other (DirectoryObject): The DirectoryObject instance to compare with.

        Returns:
        ----------
            bool: True if the path of the two DirectoryObject instances are equal, False otherwise.
        """
        if not isinstance(other, DirectoryObject):
            return False
        return self.path == other.path


class ImageObject(FileObject):
    """
    A class representing information about an image
    
    Attributes:
    ----------
        path (str): The absolute path to the file.

    Methods:
    ----------
        calculate_hash(self): Calculate the hash value of the image
    
    Properties:
    ----------
        dimensions (tuple): The dimensions of the image in pixels.
        is_corrupt (bool): Check integrity of the image
        exif (dict): Extract the EXIF data from the image
        capture_date (str or None): Return the capture date of the image if it exists in the EXIF data
    """
    def __init__(self, path):
        self._exif = None
        super().__init__(path)

    def calculate_hash(self, spec):
        """
        Calculate the hash value of the image

        Paramters:
        ---------
            spec (str): The specification for the hashing algorithm to use.

        Returns:
        ----------
            hash_value (str): The calculated hash value of the image.
            None (None)     : NoneType if an error occurs while calculating the hash

        Raises:
        --------
            UnidentifiedImageError: If the image format cannot be identified which returns None
        """

        specs = {
            "avg": lambda x: imagehash.average_hash(x),
            "dhash": lambda x: imagehash.dhash(x),
            "phash": lambda x: imagehash.phash(x)

        }
        # Ignore heic until feature is implemented to support it.
        # Excluding this has unwanted effects when comparing hash values
        if self.extension == ".heic":
            pass

        try:
            with Image.open(self.path) as img:
                hash_value = specs[spec](img)
            return hash_value
        except UnidentifiedImageError as e:
            try:
                if obj(self.path).is_corrupt:
                    print(f"\033[1;31m{self.path} is corrupt\033[0m")
                    return
            except Exception as e:
                print(
                    f'\033[1;32mError detecting corruption of "{self.path}":\033[0m\033[1;31m {e}\033[0m'
                )
                return

            print(f"Error calculating hash: {e}")
            return

    @property
    def dimensions(self):
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
    def exif(self):
        """
        Extract the EXIF data from the image

        Returns:
        ----------
            dict: A dictionary containing the EXIF data of the image.
        """
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
    def capture_date(self):
        """
        Return the capture date of the image if it exists in the EXIF data.

        Returns:
        ----------
            str or None: The capture date in the format 'YYYY:MM:DD HH:MM:SS' if it exists,
                         otherwise None.
        """
        # Iterating over all EXIF data fields
        for tag_id in self.exif:
            # Get the tag name, instead of human unreadable tag id
            tag = TAGS.get(tag_id, tag_id)
            data = self.exif.get(tag_id)
            # Decode bytes
            if isinstance(data, bytes):
                data = data.decode()
            if str(tag).startswith("DateTime"):
                return data
        return None

    @property
    def is_corrupt(self):
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
            img = Image.open(self.path)
            img.verify()
            return False
        # If an IOError or SyntaxError is raised, the image is corrupt           
        except (IOError, SyntaxError):
            return True
        except KeyboardInterrupt:
            sys.exit(0)
        # If any other exception is raised, we didnt account for something so print the error
        except Exception as e:
            print(f"Error: {e}")

    # def __str__(self):
    #     return f"""Image: {self.path}
    #         Dimensions: {self.dimensions}
    #         Hash: {self.hash}
    #         EXIF: {self.exif}
    #         Capture Date: {self.capture_date}"""


class VideoObject(FileObject):
    """
    A class representing information about a video.

    Attributes:
    ----------
        path (str): The absolute path to the file.
    
    Methods:
    ----------
        metadata (dict): Extract metadata from the video including duration, dimensions, fps, and aspect ratio.
        bitrate (int): Extract the bitrate of the video from the ffprobe output.
        is_corrupt (bool): Check integrity of the video.

    """

    def __init__(self, path):
        super().__init__(path)

    @property
    def metadata(self):
        """
        Extract metadata from the video including duration, dimensions, fps, and aspect ratio.

        Returns:
        ----------
            dict: A dictionary containing the metadata.
        """
        with VideoFileClip(self.path) as clip:
            metadata = {
                "duration": clip.duration,
                "dimensions": (clip.size[0], clip.size[1]),
                "fps": clip.fps,
                "aspect_ratio": clip.aspect_ratio,
            }
        return metadata

    @property
    def bitrate(self):
        """
        Extract the bitrate of the video from the ffprobe output.

        Returns:
        ----------
            int: The bitrate of the video in bits per second.
        """
        ffprobe_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            self.path,
        ]
        ffprobe_output = subprocess.check_output(ffprobe_cmd).decode("utf-8")
        metadata = json.loads(ffprobe_output)
        capture_date = metadata["format"]["tags"].get("creation_time")
        bit_rate = metadata["format"]["bit_rate"]
        return bit_rate

    @property
    def is_corrupt(self):
        """
        Check if the video is corrupt.

        Returns:
        ----------
            bool: True if the video is corrupt, False otherwise.
        """
        try:
            cap = cv2.VideoCapture(self.path)
            if not cap.isOpened():
                return True  # Video is corrupt
            else:
                return False  # Video is not corrupt
        except (IOError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")


def obj(path):
    if not os.path.exists(path):
        raise FileNotFoundError("Path does not exist")

    ext = os.path.splitext(path)[1].lower()
    classes = {
        ".jpg": ImageObject,  # Images
        ".jpeg": ImageObject,
        ".png": ImageObject,
        ".nef": ImageObject,
        ".mp4": VideoObject,  # Videos
        ".avi": VideoObject,
        ".mkv": VideoObject,
        ".wmv": VideoObject,
        ".webm": VideoObject,
        ".mov": VideoObject,
        ".py": ExecutableObject,  # Code files
        ".bat": ExecutableObject,
        ".sh": ExecutableObject,
        "": DirectoryObject,  # Directories,

    }
    
    cls = classes.get(ext)
    if not cls:
        return FileObject(path)
    else:
        return cls(path)


if __name__ == "__main__":
    img = ImageObject("/home/joona/Pictures/PEGBOARD.jpg")
    video = VideoObject("/mnt/ssd/compressed_obs/Dayz/blaze kill CQC.mp4")
    txtfile = FileObject("/home/joona/python/Projects/dir_oraganizer/getinfo.py")

    print(img)
    print(video)
    print(txtfile)


# f = len([f for folder in os.walk('/mnt/ssd/compressed_obs/CSGO/')
#         for f in folder])