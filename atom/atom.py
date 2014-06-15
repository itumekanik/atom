#------------------------------------------------------------------------------
# Copyright (c) 2014, Nucleic Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#------------------------------------------------------------------------------
import copy_reg

from .catom import CAtom, ClassMap, CMember


#: The string key constant used to store the type member dictionary.
CLASS_MEMBERS = '_[atom members]'


#: The string key constant used to store the type class map.
CLASS_MAP = '_[class map]'


class AtomMeta(type):
    """ The metaclass for classes derived from Atom.

    This metaclass computes the atom class map for the new type so
    that the CAtom class can allocate exactly enough space for the
    the object data slots when it instantiates an object.

    All classes deriving from Atom will be automatically slotted, which
    will prevent the creation of an instance dictionary and also the
    ability of an Atom to be weakly referenceable. If that behavior is
    required, then a subclasss should declare the appropriate slots.

    """
    def __new__(meta, name, bases, dct):
        # Unless the developer requests slots, they are automatically
        # turned off. This prevents the creation of instance dicts and
        # other space consuming features unless explicitly requested.
        if '__slots__' not in dct:
            dct['__slots__'] = ()

        # Create the class object.
        cls = type.__new__(meta, name, bases, dct)

        # Walk the mro of the class, excluding itself, in reverse order
        # collecting all of the members into a single dict. The reverse
        # update preserves the mro of overridden members.
        members = {}
        for base in reversed(cls.__mro__[1:-1]):
            if base is not CAtom and issubclass(base, CAtom):
                members.update(getattr(base, CLASS_MEMBERS))

        # Walk the current class dict to collect the new members.
        for key, value in dct.iteritems():
            if isinstance(value, CMember):
                members[key] = value

        # Creat the class map for the new class.
        class_map = ClassMap(members)

        # Store a reference to the class members and the class_map
        setattr(cls, CLASS_MEMBERS, members)
        setattr(cls, CLASS_MAP, class_map)

        return cls


def __newobj__(cls, *args):
    """ A compatibility pickler function.

    This function is not part of the public Atom api.

    """
    return cls.__new__(cls, *args)


class Atom(CAtom):
    """ The base class for defining atom objects.

    `Atom` objects are special Python objects which never allocate an
    instance dictionary unless one is explicitly requested. The storage
    for an atom is instead computed from the `Member` objects declared
    on the class. Memory is reserved for these members with no over
    allocation.

    This restriction make atom objects a bit less flexible than normal
    Python objects, but they are between 3x-10x more memory efficient
    than normal objects depending on the number of attributes.

    """
    __metaclass__ = AtomMeta

    def __reduce_ex__(self, proto):
        """ An implementation of the reduce protocol.

        This method creates a reduction tuple for Atom instances. This
        method should not be overridden by subclasses unless the author
        fully understands the rammifications.

        """
        args = (type(self),) + self.__getnewargs__()
        return (__newobj__, args, self.__getstate__())

    def __getnewargs__(self):
        """ Get the argument tuple to pass to __new__ on unpickling.

        See the Python.org docs for more information.

        """
        return ()

    def __getstate__(self):
        """ The base implementation of the pickle getstate protocol.

        This base class implementation handles the generic case where
        the object and all of its state are pickable. This includes
        state stored in Atom members, as well as any instance dict or
        slot attributes. Subclasses which require further customization
        should reimplement this method and modify the dict generated by
        this base class method.

        """
        state = {}
        state.update(getattr(self, '__dict__', {}))
        slots = copy_reg._slotnames(type(self))
        if slots:
            for name in slots:
                state[name] = getattr(self, name)
        for key in self.members():
            state[key] = getattr(self, key)
        return state

    def __setstate__(self, state):
        """ The base implementation of the pickle setstate protocol.

        This base class implementation handle the generic case of
        restoring an object using the state generated by the base
        class __getstate__ method. Subclasses which require custom
        behavior should reimplement this method.

        """
        for key, value in state.iteritems():
            setattr(self, key, value)
