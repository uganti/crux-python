"""Module contains Query model."""

from typing import Any, Dict, Iterable  # noqa: F401 pylint: disable=unused-import

from crux.models.resource import Resource
from crux.utils import DEFAULT_CHUNK_SIZE, valid_chunk_size


class Query(Resource):
    """Query Model."""

    @property
    def folder(self):
        """str: Gets and Sets the folder."""
        return self._folder

    @folder.setter
    def folder(self, folder):
        self._folder = folder

    def to_dict(self):
        # type: () -> Dict[str, Any]
        """Transforms Query object to Query dictionary.

        Returns:
            dict: Query dictionary.
        """
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "folder": self.folder,
            "type": self.type,
            "config": self.config,
            "labels": self.labels,
        }

    def run(
        self,
        format="csv",  # type: str # format name is by design pylint: disable=redefined-builtin
        params=None,  # type: Dict[str, str]
        chunk_size=DEFAULT_CHUNK_SIZE,  # type: int
        decode_unicode=False,  # type: bool
    ):
        # type(...) -> Iterable[str]
        """Method which streams the Query

        Args:
            format (str): Output format of the query. Defaults to csv.
            params (dict): Run parameters. Defaults to None.
            chunk_size (int): Chunk Size for the stream
            decode_unicode (bool): If decode_unicode is True,content will be decoded using the
                best available encoding based on the response.
                Defaults to False.

        Yields:
            bytes: Bytes of content.

        Raises:
            ValueError: If chunk size is not multiple of 256 KiB.
        """

        params = params if params else {}

        headers = {"Content-Type": "application/json", "Accept": "*/*"}

        params["format"] = format

        if not valid_chunk_size(chunk_size):
            raise ValueError("chunk_size should be multiple of 256 KiB")

        data = self.connection.api_call(
            "GET",
            ["resources", self.id, "content"],
            params=params,
            stream=True,
            headers=headers,
        )

        return data.iter_content(chunk_size=chunk_size, decode_unicode=decode_unicode)

    def download(
        self, local_path, format="csv", params=None
    ):  # It is by design pylint: disable=redefined-builtin,arguments-differ
        # type: (...) -> bool
        """Method which streams the Query

        Args:
            local_path (str): Local OS path at which resource will be downloaded.
            format (str): Output format of the query. Defaults to csv.
            params (dict): Run parameters. Defaults to None.

        Returns:
            bool: True if it is downloaded.
        """

        params = params if params else {}
        params["format"] = format
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        data = self.connection.api_call(
            "GET",
            ["resources", self.id, "content"],
            params=params,
            stream=True,
            headers=headers,
        )

        with open(local_path, "w") as local_file:
            for line in data.iter_lines():
                if line:
                    dcd_line = line.decode("utf-8")
                    local_file.write(dcd_line + "\n")
        return True
