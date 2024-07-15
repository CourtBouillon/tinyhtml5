"""A collection of modules for building different kinds of trees from HTML
documents.

To create a treebuilder for a new type of tree, you need to do
implement several things:

1. A set of classes for various types of elements: Document, Doctype, Comment,
   Element. These must implement the interface of ``treebuilder.Node``
   (although comment nodes have a different signature for their constructor,
   see ``treebuilder.Comment``) Textual content may also be implemented
   as another node type, or not, as your tree implementation requires.

2. A treebuilder object (called ``TreeBuilder`` by convention) that inherits
   from ``treebuilders.TreeBuilder``. This has 4 required attributes:

   * ``documentClass`` - the class to use for the bottommost node of a document
   * ``elementClass`` - the class to use for HTML Elements
   * ``commentClass`` - the class to use for comments
   * ``doctypeClass`` - the class to use for doctypes

   It also has one required method:

   * ``getDocument`` - Returns the root node of the complete document tree

3. If you wish to run the unit tests, you must also create a ``testSerializer``
   method on your treebuilder which accepts a node and returns a string
   containing Node and its children serialized according to the format used in
   the unittests

"""

import re
import xml.etree.ElementTree as default_etree
from copy import copy
from types import ModuleType

from six import text_type

from .constants import scopingElements, tableInsertModeElements, namespaces, prefixes
from . import _ihatexml


treeBuilderCache = {}


def getTreeBuilder(treeType, implementation=None, **kwargs):
    """Get a TreeBuilder class for various types of trees with built-in support

    :arg treeType: the name of the tree type required (case-insensitive). Supported
        values are:

        * "dom" - A generic builder for DOM implementations, defaulting to a
          xml.dom.minidom based implementation.
        * "etree" - A generic builder for tree implementations exposing an
          ElementTree-like interface, defaulting to xml.etree.cElementTree if
          available and xml.etree.ElementTree if not.
        * "lxml" - A etree-based builder for lxml.etree, handling limitations
          of lxml's implementation.

    :arg implementation: (Currently applies to the "etree" and "dom" tree
        types). A module implementing the tree type e.g. xml.etree.ElementTree
        or xml.etree.cElementTree.

    :arg kwargs: Any additional options to pass to the TreeBuilder when
        creating it.

    Example:

    >>> from html5lib.treebuilder import getTreeBuilder
    >>> builder = getTreeBuilder('etree')

    """

    treeType = treeType.lower()
    if treeType not in treeBuilderCache:
        if treeType == "etree":
            if implementation is None:
                implementation = default_etree
            # NEVER cache here, caching is done in the etree submodule
            return getETreeModule(implementation, **kwargs).TreeBuilder
        else:
            raise ValueError("""Unrecognised treebuilder "%s" """ % treeType)
    return treeBuilderCache.get(treeType)


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


class Node(object):
    """Represents an item in the tree"""
    def __init__(self, name):
        """Creates a Node

        :arg name: The tag name associated with the node

        """
        # The tag name associated with the node
        self.name = name
        # The parent of the current node (or None for the document node)
        self.parent = None
        # The value of the current node (applies to text nodes and comments)
        self.value = None
        # A dict holding name -> value pairs for attributes of the node
        self.attributes = {}
        # A list of child nodes of the current node. This must include all
        # elements but not necessarily other node types.
        self.childNodes = []
        # A list of miscellaneous flags that can be set on the node.
        self._flags = []

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

    def appendChild(self, node):
        """Insert node as a child of the current node

        :arg node: the node to insert

        """
        raise NotImplementedError

    def insertText(self, data, insertBefore=None):
        """Insert data as text in the current node, positioned before the
        start of node insertBefore or to the end of the node's text.

        :arg data: the data to insert

        :arg insertBefore: True if you want to insert the text before the node
            and False if you want to insert it after the node

        """
        raise NotImplementedError

    def insertBefore(self, node, refNode):
        """Insert node as a child of the current node, before refNode in the
        list of child nodes. Raises ValueError if refNode is not a child of
        the current node

        :arg node: the node to insert

        :arg refNode: the child node to insert the node before

        """
        raise NotImplementedError

    def removeChild(self, node):
        """Remove node from the children of the current node

        :arg node: the child node to remove

        """
        raise NotImplementedError

    def reparentChildren(self, newParent):
        """Move all the children of the current node to newParent.
        This is needed so that trees that don't store text as nodes move the
        text in the correct way

        :arg newParent: the node to move all this node's children to

        """
        # XXX - should this method be made more general?
        for child in self.childNodes:
            newParent.appendChild(child)
        self.childNodes = []

    def cloneNode(self):
        """Return a shallow copy of the current node i.e. a node with the same
        name and attributes but with no parent or child nodes
        """
        raise NotImplementedError

    def hasContent(self):
        """Return true if the node has children or text, false otherwise
        """
        raise NotImplementedError


class ActiveFormattingElements(list):
    def append(self, node):
        """Append node to the end of the list."""
        equalCount = 0
        if node != Marker:
            for element in self[::-1]:
                if element == Marker:
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


class BaseTreeBuilder(object):
    """Base treebuilder implementation

    * documentClass - the class to use for the bottommost node of a document
    * elementClass - the class to use for HTML Elements
    * commentClass - the class to use for comments
    * doctypeClass - the class to use for doctypes

    """
    # pylint:disable=not-callable

    # Document class
    documentClass = None

    # The class to use for creating a node
    elementClass = None

    # The class to use for creating comments
    commentClass = None

    # The class to use for creating doctypes
    doctypeClass = None

    # Fragment class
    fragmentClass = None

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

        self.document = self.documentClass()

    def elementInScope(self, target, variant=None):

        # If we pass a node in we match that. if we pass a string
        # match any node with that name
        exactNode = hasattr(target, "nameTuple")
        if not exactNode:
            if isinstance(target, text_type):
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
        if entry == Marker or entry in self.openElements:
            return

        # Step 6
        while entry != Marker and entry not in self.openElements:
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
        while self.activeFormattingElements and entry != Marker:
            entry = self.activeFormattingElements.pop()

    def elementInActiveFormattingElements(self, name):
        """Check if an element exists between the end of the active
        formatting elements and the last marker. If it does, return it, else
        return false"""

        for item in self.activeFormattingElements[::-1]:
            # Check for Marker first because if it's a Marker it doesn't have a
            # name attribute.
            if item == Marker:
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

        doctype = self.doctypeClass(name, publicId, systemId)
        self.document.appendChild(doctype)

    def insertComment(self, token, parent=None):
        if parent is None:
            parent = self.openElements[-1]
        parent.appendChild(self.commentClass(token["data"]))

    def createElement(self, token):
        """Create an element but don't insert it anywhere"""
        name = token["name"]
        namespace = token.get("namespace", self.defaultNamespace)
        element = self.elementClass(name, namespace)
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
        assert isinstance(name, text_type), "Element %s not unicode" % name
        namespace = token.get("namespace", self.defaultNamespace)
        element = self.elementClass(name, namespace)
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
        return self.document

    def getFragment(self):
        """Return the final fragment"""
        # assert self.innerHTML
        fragment = self.fragmentClass()
        self.openElements[0].reparentChildren(fragment)
        return fragment

    def testSerializer(self, node):
        """Serialize the subtree of node in the format required by unit tests

        :arg node: the node from which to start serializing

        """
        raise NotImplementedError

tag_regexp = re.compile("{([^}]*)}(.*)")


def getETreeBuilder(ElementTreeImplementation, fullTree=False):
    ElementTree = ElementTreeImplementation
    ElementTreeCommentType = ElementTree.Comment("asd").tag

    class Element(Node):
        def __init__(self, name, namespace=None):
            self._name = name
            self._namespace = namespace
            self._element = ElementTree.Element(self._getETreeTag(name,
                                                                  namespace))
            if namespace is None:
                self.nameTuple = namespaces["html"], self._name
            else:
                self.nameTuple = self._namespace, self._name
            self.parent = None
            self._childNodes = []
            self._flags = []

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

        attributes = property(_getAttributes, _setAttributes)

        def _getChildNodes(self):
            return self._childNodes

        def _setChildNodes(self, value):
            del self._element[:]
            self._childNodes = []
            for element in value:
                self.insertChild(element)

        childNodes = property(_getChildNodes, _setChildNodes)

        def hasContent(self):
            """Return true if the node has children or text"""
            return bool(self._element.text or len(self._element))

        def appendChild(self, node):
            self._childNodes.append(node)
            self._element.append(node._element)
            node.parent = self

        def insertBefore(self, node, refNode):
            index = list(self._element).index(refNode._element)
            self._element.insert(index, node._element)
            node.parent = self

        def removeChild(self, node):
            self._childNodes.remove(node)
            self._element.remove(node._element)
            node.parent = None

        def insertText(self, data, insertBefore=None):
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
            element = type(self)(self.name, self.namespace)
            if self._element.attrib:
                element._element.attrib = copy(self._element.attrib)
            return element

        def reparentChildren(self, newParent):
            if newParent.childNodes:
                newParent.childNodes[-1]._element.tail += self._element.text
            else:
                if not newParent._element.text:
                    newParent._element.text = ""
                if self._element.text is not None:
                    newParent._element.text += self._element.text
            self._element.text = ""
            Node.reparentChildren(self, newParent)

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

    def testSerializer(element):
        rv = []

        def serializeElement(element, indent=0):
            if not hasattr(element, "tag"):
                element = element.getroot()
            if element.tag == "<!DOCTYPE>":
                if element.get("publicId") or element.get("systemId"):
                    publicId = element.get("publicId") or ""
                    systemId = element.get("systemId") or ""
                    rv.append("""<!DOCTYPE %s "%s" "%s">""" %
                              (element.text, publicId, systemId))
                else:
                    rv.append("<!DOCTYPE %s>" % (element.text,))
            elif element.tag == "DOCUMENT_ROOT":
                rv.append("#document")
                if element.text is not None:
                    rv.append("|%s\"%s\"" % (' ' * (indent + 2), element.text))
                if element.tail is not None:
                    raise TypeError("Document node cannot have tail")
                if hasattr(element, "attrib") and len(element.attrib):
                    raise TypeError("Document node cannot have attributes")
            elif element.tag == ElementTreeCommentType:
                rv.append("|%s<!-- %s -->" % (' ' * indent, element.text))
            else:
                assert isinstance(element.tag, text_type), \
                    "Expected unicode, got %s, %s" % (type(element.tag), element.tag)
                nsmatch = tag_regexp.match(element.tag)

                if nsmatch is None:
                    name = element.tag
                else:
                    ns, name = nsmatch.groups()
                    prefix = prefixes[ns]
                    name = "%s %s" % (prefix, name)
                rv.append("|%s<%s>" % (' ' * indent, name))

                if hasattr(element, "attrib"):
                    attributes = []
                    for name, value in element.attrib.items():
                        nsmatch = tag_regexp.match(name)
                        if nsmatch is not None:
                            ns, name = nsmatch.groups()
                            prefix = prefixes[ns]
                            attr_string = "%s %s" % (prefix, name)
                        else:
                            attr_string = name
                        attributes.append((attr_string, value))

                    for name, value in sorted(attributes):
                        rv.append('|%s%s="%s"' % (' ' * (indent + 2), name, value))
                if element.text:
                    rv.append("|%s\"%s\"" % (' ' * (indent + 2), element.text))
            indent += 2
            for child in element:
                serializeElement(child, indent)
            if element.tail:
                rv.append("|%s\"%s\"" % (' ' * (indent - 2), element.tail))
        serializeElement(element, 0)

        return "\n".join(rv)

    def tostring(element):  # pylint:disable=unused-variable
        """Serialize an element and its child nodes to a string"""
        rv = []
        filter = _ihatexml.InfosetFilter()

        def serializeElement(element):
            if isinstance(element, ElementTree.ElementTree):
                element = element.getroot()

            if element.tag == "<!DOCTYPE>":
                if element.get("publicId") or element.get("systemId"):
                    publicId = element.get("publicId") or ""
                    systemId = element.get("systemId") or ""
                    rv.append("""<!DOCTYPE %s PUBLIC "%s" "%s">""" %
                              (element.text, publicId, systemId))
                else:
                    rv.append("<!DOCTYPE %s>" % (element.text,))
            elif element.tag == "DOCUMENT_ROOT":
                if element.text is not None:
                    rv.append(element.text)
                if element.tail is not None:
                    raise TypeError("Document node cannot have tail")
                if hasattr(element, "attrib") and len(element.attrib):
                    raise TypeError("Document node cannot have attributes")

                for child in element:
                    serializeElement(child)

            elif element.tag == ElementTreeCommentType:
                rv.append("<!--%s-->" % (element.text,))
            else:
                # This is assumed to be an ordinary element
                if not element.attrib:
                    rv.append("<%s>" % (filter.fromXmlName(element.tag),))
                else:
                    attr = " ".join(["%s=\"%s\"" % (
                        filter.fromXmlName(name), value)
                        for name, value in element.attrib.items()])
                    rv.append("<%s %s>" % (element.tag, attr))
                if element.text:
                    rv.append(element.text)

                for child in element:
                    serializeElement(child)

                rv.append("</%s>" % (element.tag,))

            if element.tail:
                rv.append(element.tail)

        serializeElement(element)

        return "".join(rv)

    class TreeBuilder(BaseTreeBuilder):  # pylint:disable=unused-variable
        documentClass = Document
        doctypeClass = DocumentType
        elementClass = Element
        commentClass = Comment
        fragmentClass = DocumentFragment
        implementation = ElementTreeImplementation

        def testSerializer(self, element):
            return testSerializer(element)

        def getDocument(self):
            if fullTree:
                return self.document._element
            else:
                if self.defaultNamespace is not None:
                    return self.document._element.find(
                        "{%s}html" % self.defaultNamespace)
                else:
                    return self.document._element.find("html")

        def getFragment(self):
            return TreeBuilder.getFragment(self)._element

    return locals()


def moduleFactoryFactory(factory):
    moduleCache = {}

    def moduleFactory(baseModule, *args, **kwargs):
        if isinstance(ModuleType.__name__, type("")):
            name = "_%s_factory" % baseModule.__name__
        else:
            name = b"_%s_factory" % baseModule.__name__

        kwargs_tuple = tuple(kwargs.items())

        try:
            return moduleCache[name][args][kwargs_tuple]
        except KeyError:
            mod = ModuleType(name)
            objs = factory(baseModule, *args, **kwargs)
            mod.__dict__.update(objs)
            if "name" not in moduleCache:
                moduleCache[name] = {}
            if "args" not in moduleCache[name]:
                moduleCache[name][args] = {}
            if "kwargs" not in moduleCache[name][args]:
                moduleCache[name][args][kwargs_tuple] = {}
            moduleCache[name][args][kwargs_tuple] = mod
            return mod

    return moduleFactory


getETreeModule = moduleFactoryFactory(getETreeBuilder)
