"""Tree builder."""

from xml.etree import ElementTree
from copy import copy

from .constants import scopingElements, tableInsertModeElements, namespaces


# The scope markers are inserted when entering object elements,
# marquees, table cells, and table captions, and are used to prevent formatting
# from "leaking" into tables, object elements, and marquees.
Marker = None

listElementsMap = {
    None: (frozenset(scopingElements), False),
    "button": (frozenset(scopingElements | {(namespaces["html"], "button")}), False),
    "list": (frozenset(scopingElements | {(namespaces["html"], "ol"),
                                          (namespaces["html"], "ul")}), False),
    "table": (frozenset([(namespaces["html"], "html"),
                         (namespaces["html"], "table")]), False),
    "select": (frozenset([(namespaces["html"], "optgroup"),
                          (namespaces["html"], "option")]), True)
}


class ActiveFormattingElements(list):
    def append(self, node):
        """Append node to the end of the list."""
        equalCount = 0
        if node is not Marker:
            for element in self[::-1]:
                if element is Marker:
                    break
                if self.nodesEqual(element, node):
                    equalCount += 1
                if equalCount == 3:
                    self.remove(element)
                    break
        list.append(self, node)

    def nodesEqual(self, node1, node2):
        if not node1.nameTuple == node2.nameTuple:
            return False

        if not node1.attributes == node2.attributes:
            return False

        return True


class Element:
    def __init__(self, name, namespace=None):
        self._name = name
        self._namespace = namespace
        self._element = ElementTree.Element(self._getETreeTag(name, namespace))
        if namespace is None:
            self.nameTuple = namespaces["html"], self._name
        else:
            self.nameTuple = self._namespace, self._name
        self._childNodes = []
        self._flags = []

        # The parent of the current node (or None for the document node)
        self.parent = None

    def __str__(self):
        attributesStr = " ".join(["%s=\"%s\"" % (name, value)
                                  for name, value in
                                  self.attributes.items()])
        if attributesStr:
            return "<%s %s>" % (self.name, attributesStr)
        else:
            return "<%s>" % (self.name)

    def __repr__(self):
        return "<%s>" % (self.name)

    def _getETreeTag(self, name, namespace):
        if namespace is None:
            etree_tag = name
        else:
            etree_tag = "{%s}%s" % (namespace, name)
        return etree_tag

    def _setName(self, name):
        self._name = name
        self._element.tag = self._getETreeTag(self._name, self._namespace)

    def _getName(self):
        return self._name

    # The tag name associated with the node
    name = property(_getName, _setName)

    def _setNamespace(self, namespace):
        self._namespace = namespace
        self._element.tag = self._getETreeTag(self._name, self._namespace)

    def _getNamespace(self):
        return self._namespace

    namespace = property(_getNamespace, _setNamespace)

    def _getAttributes(self):
        return self._element.attrib

    def _setAttributes(self, attributes):
        el_attrib = self._element.attrib
        el_attrib.clear()
        if attributes:
            # calling .items _always_ allocates, and the above truthy check is cheaper than the
            # allocation on average
            for key, value in attributes.items():
                if isinstance(key, tuple):
                    name = "{%s}%s" % (key[2], key[1])
                else:
                    name = key
                el_attrib[name] = value

    # A dict holding name -> value pairs for attributes of the node
    attributes = property(_getAttributes, _setAttributes)

    def _getChildNodes(self):
        return self._childNodes

    def _setChildNodes(self, value):
        del self._element[:]
        self._childNodes = []
        for element in value:
            self.insertChild(element)

    # A list of child nodes of the current node. This must include all
    # elements but not necessarily other node types.
    childNodes = property(_getChildNodes, _setChildNodes)

    def hasContent(self):
        """Return true if the node has children or text, false otherwise."""
        return bool(self._element.text or len(self._element))

    def appendChild(self, node):
        """Insert node as a child of the current node

        :arg node: the node to insert

        """
        self._childNodes.append(node)
        self._element.append(node._element)
        node.parent = self

    def insertBefore(self, node, refNode):
        """Insert node as a child of the current node, before refNode in the
        list of child nodes. Raises ValueError if refNode is not a child of
        the current node

        :arg node: the node to insert

        :arg refNode: the child node to insert the node before

        """
        index = list(self._element).index(refNode._element)
        self._element.insert(index, node._element)
        node.parent = self

    def removeChild(self, node):
        """Remove node from the children of the current node

        :arg node: the child node to remove

        """
        self._childNodes.remove(node)
        self._element.remove(node._element)
        node.parent = None

    def insertText(self, data, insertBefore=None):
        """Insert data as text in the current node, positioned before the
        start of node insertBefore or to the end of the node's text.

        :arg data: the data to insert

        :arg insertBefore: True if you want to insert the text before the node
            and False if you want to insert it after the node

        """
        if not len(self._element):
            if not self._element.text:
                self._element.text = ""
            self._element.text += data
        elif insertBefore is None:
            # Insert the text as the tail of the last child element
            if not self._element[-1].tail:
                self._element[-1].tail = ""
            self._element[-1].tail += data
        else:
            # Insert the text before the specified node
            children = list(self._element)
            index = children.index(insertBefore._element)
            if index > 0:
                if not self._element[index - 1].tail:
                    self._element[index - 1].tail = ""
                self._element[index - 1].tail += data
            else:
                if not self._element.text:
                    self._element.text = ""
                self._element.text += data

    def cloneNode(self):
        """Return a shallow copy of the current node i.e. a node with the same
        name and attributes but with no parent or child nodes
        """
        element = type(self)(self.name, self.namespace)
        if self._element.attrib:
            element._element.attrib = copy(self._element.attrib)
        return element

    def reparentChildren(self, newParent):
        """Move all the children of the current node to newParent.
        This is needed so that trees that don't store text as nodes move the
        text in the correct way

        :arg newParent: the node to move all this node's children to

        """
        if newParent.childNodes:
            newParent.childNodes[-1]._element.tail += self._element.text
        else:
            if not newParent._element.text:
                newParent._element.text = ""
            if self._element.text is not None:
                newParent._element.text += self._element.text
        self._element.text = ""
        for child in self.childNodes:
            newParent.appendChild(child)
        self.childNodes = []


class Comment(Element):
    def __init__(self, data):
        # Use the superclass constructor to set all properties on the
        # wrapper element
        self._element = ElementTree.Comment(data)
        self.parent = None
        self._childNodes = []
        self._flags = []

    def _getData(self):
        return self._element.text

    def _setData(self, value):
        self._element.text = value

    data = property(_getData, _setData)


class DocumentType(Element):
    def __init__(self, name, publicId, systemId):
        Element.__init__(self, "<!DOCTYPE>")
        self._element.text = name
        self.publicId = publicId
        self.systemId = systemId

    def _getPublicId(self):
        return self._element.get("publicId", "")

    def _setPublicId(self, value):
        if value is not None:
            self._element.set("publicId", value)

    publicId = property(_getPublicId, _setPublicId)

    def _getSystemId(self):
        return self._element.get("systemId", "")

    def _setSystemId(self, value):
        if value is not None:
            self._element.set("systemId", value)

    systemId = property(_getSystemId, _setSystemId)


class Document(Element):
    def __init__(self):
        Element.__init__(self, "DOCUMENT_ROOT")


class DocumentFragment(Element):
    def __init__(self):
        Element.__init__(self, "DOCUMENT_FRAGMENT")


class TreeBuilder:
    """Tree builder."""

    def __init__(self, namespaceHTMLElements):
        """Create a TreeBuilder

        :arg namespaceHTMLElements: whether or not to namespace HTML elements

        """
        if namespaceHTMLElements:
            self.defaultNamespace = "http://www.w3.org/1999/xhtml"
        else:
            self.defaultNamespace = None
        self.reset()

    def reset(self):
        self.openElements = []
        self.activeFormattingElements = ActiveFormattingElements()

        # XXX - rename these to headElement, formElement
        self.headPointer = None
        self.formPointer = None

        self.insertFromTable = False

        self.document = Document()

    def elementInScope(self, target, variant=None):

        # If we pass a node in we match that. if we pass a string
        # match any node with that name
        exactNode = hasattr(target, "nameTuple")
        if not exactNode:
            if isinstance(target, str):
                target = (namespaces["html"], target)
            assert isinstance(target, tuple)

        listElements, invert = listElementsMap[variant]

        for node in reversed(self.openElements):
            if exactNode and node == target:
                return True
            elif not exactNode and node.nameTuple == target:
                return True
            elif (invert ^ (node.nameTuple in listElements)):
                return False

        assert False  # We should never reach this point

    def reconstructActiveFormattingElements(self):
        # Within this algorithm the order of steps described in the
        # specification is not quite the same as the order of steps in the
        # code. It should still do the same though.

        # Step 1: stop the algorithm when there's nothing to do.
        if not self.activeFormattingElements:
            return

        # Step 2 and step 3: we start with the last element. So i is -1.
        i = len(self.activeFormattingElements) - 1
        entry = self.activeFormattingElements[i]
        if entry is Marker or entry in self.openElements:
            return

        # Step 6
        while entry is not Marker and entry not in self.openElements:
            if i == 0:
                # This will be reset to 0 below
                i = -1
                break
            i -= 1
            # Step 5: let entry be one earlier in the list.
            entry = self.activeFormattingElements[i]

        while True:
            # Step 7
            i += 1

            # Step 8
            entry = self.activeFormattingElements[i]
            clone = entry.cloneNode()  # Mainly to get a new copy of the attributes

            # Step 9
            element = self.insertElement({"type": "StartTag",
                                          "name": clone.name,
                                          "namespace": clone.namespace,
                                          "data": clone.attributes})

            # Step 10
            self.activeFormattingElements[i] = element

            # Step 11
            if element == self.activeFormattingElements[-1]:
                break

    def clearActiveFormattingElements(self):
        entry = self.activeFormattingElements.pop()
        while self.activeFormattingElements and entry is not Marker:
            entry = self.activeFormattingElements.pop()

    def elementInActiveFormattingElements(self, name):
        """Check if an element exists between the end of the active
        formatting elements and the last marker. If it does, return it, else
        return false"""

        for item in self.activeFormattingElements[::-1]:
            # Check for Marker first because if it's a Marker it doesn't have a
            # name attribute.
            if item is Marker:
                break
            elif item.name == name:
                return item
        return False

    def insertRoot(self, token):
        element = self.createElement(token)
        self.openElements.append(element)
        self.document.appendChild(element)

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        doctype = DocumentType(name, publicId, systemId)
        self.document.appendChild(doctype)

    def insertComment(self, token, parent=None):
        if parent is None:
            parent = self.openElements[-1]
        parent.appendChild(Comment(token["data"]))

    def createElement(self, token):
        """Create an element but don't insert it anywhere"""
        name = token["name"]
        namespace = token.get("namespace", self.defaultNamespace)
        element = Element(name, namespace)
        element.attributes = token["data"]
        return element

    def _getInsertFromTable(self):
        return self._insertFromTable

    def _setInsertFromTable(self, value):
        """Switch the function used to insert an element from the
        normal one to the misnested table one and back again"""
        self._insertFromTable = value
        if value:
            self.insertElement = self.insertElementTable
        else:
            self.insertElement = self.insertElementNormal

    insertFromTable = property(_getInsertFromTable, _setInsertFromTable)

    def insertElementNormal(self, token):
        name = token["name"]
        assert isinstance(name, str), "Element %s not unicode" % name
        namespace = token.get("namespace", self.defaultNamespace)
        element = Element(name, namespace)
        element.attributes = token["data"]
        self.openElements[-1].appendChild(element)
        self.openElements.append(element)
        return element

    def insertElementTable(self, token):
        """Create an element and insert it into the tree"""
        element = self.createElement(token)
        if self.openElements[-1].name not in tableInsertModeElements:
            return self.insertElementNormal(token)
        else:
            # We should be in the InTable mode. This means we want to do
            # special magic element rearranging
            parent, insertBefore = self.getTableMisnestedNodePosition()
            if insertBefore is None:
                parent.appendChild(element)
            else:
                parent.insertBefore(element, insertBefore)
            self.openElements.append(element)
        return element

    def insertText(self, data, parent=None):
        """Insert text data."""
        if parent is None:
            parent = self.openElements[-1]

        if (not self.insertFromTable or (self.insertFromTable and
                                         self.openElements[-1].name
                                         not in tableInsertModeElements)):
            parent.insertText(data)
        else:
            # We should be in the InTable mode. This means we want to do
            # special magic element rearranging
            parent, insertBefore = self.getTableMisnestedNodePosition()
            parent.insertText(data, insertBefore)

    def getTableMisnestedNodePosition(self):
        """Get the foster parent element, and sibling to insert before
        (or None) when inserting a misnested table node"""
        # The foster parent element is the one which comes before the most
        # recently opened table element
        # XXX - this is really inelegant
        lastTable = None
        fosterParent = None
        insertBefore = None
        for elm in self.openElements[::-1]:
            if elm.name == "table":
                lastTable = elm
                break
        if lastTable:
            # XXX - we should really check that this parent is actually a
            # node here
            if lastTable.parent:
                fosterParent = lastTable.parent
                insertBefore = lastTable
            else:
                fosterParent = self.openElements[
                    self.openElements.index(lastTable) - 1]
        else:
            fosterParent = self.openElements[0]
        return fosterParent, insertBefore

    def generateImpliedEndTags(self, exclude=None):
        name = self.openElements[-1].name
        # XXX td, th and tr are not actually needed
        if (name in frozenset(("dd", "dt", "li", "option", "optgroup", "p", "rp", "rt")) and
                name != exclude):
            self.openElements.pop()
            # XXX This is not entirely what the specification says. We should
            # investigate it more closely.
            self.generateImpliedEndTags(exclude)

    def getDocument(self):
        """Return the final tree"""
        if self.defaultNamespace is not None:
            return self.document._element.find(
                "{%s}html" % self.defaultNamespace)
        else:
            return self.document._element.find("html")

    def getFragment(self):
        """Return the final fragment"""
        # assert self.innerHTML
        fragment = DocumentFragment()
        self.openElements[0].reparentChildren(fragment)
        return fragment._element
