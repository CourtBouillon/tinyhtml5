import codecs
from collections import defaultdict


class Data:
    def __init__(self, filename, newTestHeading="data", encoding="utf8"):
        if encoding is None:
            self.f = open(filename, mode="rb")
        else:
            self.f = codecs.open(filename, encoding=encoding)
        self.encoding = encoding
        self.newTestHeading = newTestHeading

    def __iter__(self):
        data = defaultdict(lambda: None)
        key = None
        for line in self.f:
            heading = self.is_section_heading(line)
            if heading:
                if data and heading == self.newTestHeading:
                    # Remove trailing newline
                    data[key] = data[key][:-1]
                    yield self.normalise_output(data)
                    data = defaultdict(lambda: None)
                key = heading
                data[key] = "" if self.encoding else b""
            elif key is not None:
                data[key] += line
        if data:
            yield self.normalise_output(data)

    def is_section_heading(self, line):
        """If the current heading is a test section heading return the heading,
        otherwise return False"""
        # print(line)
        if line.startswith("#" if self.encoding else b"#"):
            return line[1:].strip()
        else:
            return False

    def normalise_output(self, data):
        # Remove trailing newlines
        for key, value in data.items():
            if value.endswith("\n" if self.encoding else b"\n"):
                data[key] = value[:-1]
        return data


