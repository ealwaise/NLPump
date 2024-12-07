"""
This module contains the SSCFile class, which is used to parse .ssc
files.
"""

import os, re


class SSCFile:
    """
    Store the parsed contents of an .SSC file.

    An .ssc file consists of a global header section and various
    stepchart sections, each of which has various attributes. This
    parser will separate the two and get the attributes of each.
    """

    def __init__(self, file_path: str, verbose=True):
        """
        Initializes an SSCFile object from a path to an .ssc file.

        Arguments
        ---------
        file_path : str
            A file path to an .ssc file.
        verbose : bool
            If true, prints a message if the parsing is successful.
        """
        # Raise an error if the file name is not a valid path.
        if not os.path.isfile(file_path):
            raise ValueError(f"{file_path} is not a valid file path.")

        # Raise an error if the file is not an .ssc file.
        ext = os.path.splitext(file_path)[-1].lower()
        if ext != ".ssc":
            raise ValueError(f"{file_path} is not an .ssc file")

        # Find sections.
        lines = open(file_path, "r", encoding="utf-8").readlines()
        sections = self.parse_sections(lines)

        # Get global attributes.
        global_header = sections["global_header"]
        self.global_attributes = self.parse_attributes(global_header)

        # Parse stepchart sections.
        stepcharts = sections["stepcharts"]
        stepcharts = self.parse_stepcharts(stepcharts)
        self.stepcharts = stepcharts

        # Print a message when parsing is complete.
        if verbose:
            name = file_path.split(os.path.sep)[-1]
            print(f"{name} successfuly parsed.")

    def parse_sections(self, lines: list[str]) -> dict:
        """
        Parse the sections of the .ssc file.

        An .ssc file contains a global header section, which contains
        stepchart-agnostic data, and sections corresponding to
        individual stepcharts. The global header section should contain
        an attribute giving the song title, while each stepchart
        section should contain an attribute giving the step type (pump-
        single, pump-double, etc.) If any of these attribtues are
        missing, an AssertionError will be raised.

        Arguments
        ---------
        lines : list[str]
            A list containing the lines of text in the .ssc file.

        Returns
        -------
        parsed_sections: dict
            A dictionary whose values are the global header section and
            a list containing the stepchart sections.
        """
        # Remove comments.
        lines = filter(lambda s: not re.match("[=<>\/]", s), lines)

        delim = "#NOTEDATA:;"  # This separates stepchart sections.
        all_lines = "\n".join(lines)
        sections = all_lines.split(delim)

        # Raise an error if the song title is not found.
        assert (
            "#TITLE" in sections[0]
        ), f"Error in parsing {self.file_path}: missing song title."

        # Raise an error if the step type is not found.
        for section in sections[1:]:
            assert (
                "#STEPSTYPE" in section
            ), f"Error in parsing {self.file_path}: missing step type."

        parsed_sections = {
            "global_header": sections[0],
            "stepcharts": sections[1:],
        }

        return parsed_sections

    def parse_attributes(self, header: str) -> dict:
        """
        Parse the attributes of the header section of the .ssc file.

        Each section of the .ssc file contains a header. A section
        header contains various attributes of the form
        '#[KEY]:[VALUE];'.

        Arguments
        ---------
        header : str
            The header of a section of the .ssc file.

        Returns
        -------
        attributes : dict
            Maps the key of each attribute to its corresponding value.
        """
        # Insert missing semicolons and remove extras.
        header = re.sub("\n+", "", header)
        header = header.replace("#", ";#")
        header = header.replace(";;", ";")
        header = header[1:]

        # Replace escaped semicolons/number signs to prevent splitting issues.
        header = header.replace("\\:", "Ͽ")
        header = header.replace("\\#", "Ͼ")

        # Attribute key and values are separated by a semicolon.
        key_vals = header.split(";")

        # Get the key and value of all attributes.
        atts = dict()
        for key_val in key_vals:
            # Ignore empty attributes.
            if not key_val:
                continue

            key_val = key_val.split("//")[0]  # Remove comments.
            if ":" in key_val:
                key, val = key_val.split(":")[:2]
            if key[0] == "#":
                key = key[1:]
                # Restore escaped semicolons/number signs.
                val = val.replace("Ͽ", ":")
                val = val.replace("Ͼ", "#")

                atts[key] = val

        return atts

    def parse_stepcharts(self, stepcharts: list[str]) -> list[dict]:
        """
        Parse the stepchart sections of the .ssc file.

        Each stepchart section contains a header section and a note
        section. This fuction will separate the two and get the
        attributes stored in the header section.

        Arguments
        ---------
        stepcharts : list[str]
            A list containing the stepchart sections of the .ssc file.

        Returns
        -------
        parsed_stepcharts: list[dict]
            A list containing the parsed stepchart sections.
        """
        delim = "#NOTES:"  # This separates the header from the stepcharts.
        parsed_stepcharts = []

        # Parse the attributes and notes of each stepchart.
        for stepchart in stepcharts:
            parsed_stepchart = dict()
            sections = stepchart.split(delim)
            # Ignore blank stepcharts.
            if len(sections) < 2:
                continue

            header, notes = sections[0], sections[1]
            attributes = self.parse_attributes(header)

            # Find the end of the notes and remove trailing spaces.
            notes = notes[: notes.index(";")]
            notes = notes.strip()

            parsed_stepchart["attributes"] = attributes
            parsed_stepchart["notes"] = notes
            parsed_stepcharts.append(parsed_stepchart)

            # Add initial timing data if it's missing.
            atts = parsed_stepchart["attributes"]
            for key in ["BPMS", "TICKCOUNTS", "SPEEDS", "SCROLLS", "OFFSET"]:
                atts[key] = atts.get(key, self.global_attributes[key])

        return parsed_stepcharts
