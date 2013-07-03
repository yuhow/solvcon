# -*- coding: UTF-8 -*-
#
# Copyright (C) 2008-2013 Yung-Yu Chen <yyc@solvcon.net>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""
Basic code for :py:mod:`solvcon.case`.
"""


from . import gendata
from . import anchor
from . import hook


class _ArrangementRegistry(gendata.SingleAssignDict, gendata.AttributeDict):
    """
    Arrangement registry class.  An "arrangement" is a callable that returns a
    :py:class:`MeshCase` object.
    """
    def __setitem__(self, key, value):
        """
        >>> regy = _ArrangementRegistry()
        >>> # assigning a key to a function is OK.
        >>> regy['func1'] = lambda a: a
        >>> # assigning a key to anything else isn't allowed.
        >>> regy['func2'] = None
        Traceback (most recent call last):
          ...
        ValueError: None should be a callable, but a <type 'NoneType'> is got.
        """
        if not callable(value):
            raise ValueError("%s should be a callable, but a %s is got." % (
                str(value), str(type(value))))
        super(_ArrangementRegistry, self).__setitem__(key, value)

arrangements = _ArrangementRegistry()  # overall registry singleton.


class CaseInfoMeta(type):
    """
    Meta class for case information class.
    """
    def __new__(cls, name, bases, namespace):
        newcls = super(CaseInfoMeta, cls).__new__(cls, name, bases, namespace)
        # incremental modification of defdict.
        defdict = {}
        for base in bases:
            defdict.update(getattr(base, 'defdict', {}))
        defdict.update(newcls.defdict)
        newcls.defdict = defdict
        # create different simulation registry objects for case classes.
        newcls.arrangements = _ArrangementRegistry()
        return newcls


class CaseInfo(dict):
    """
    Generic case information abstract class.  It's the base class that all case
    information classes should subclass, to form hierarchical information 
    object.
    """

    __metaclass__ = CaseInfoMeta

    defdict = {}

    def __getattr__(self, name):
        """
        Consult self dictionary for attribute.  It's a shorthand.
        """
        if name == '__setstate__':
            raise AttributeError
        return self[name]

    def __setattr__(self, name, value):
        """
        Save to self dictionary first, then self object table.

        @note: This method is overriden as a stupid-preventer.  It makes
        attribute setting consistent with attribute getting.
        """
        if name in self:
            self[name] = value
        else:
            super(CaseInfo, self).__setattr__(name, value)

    def _set_through(self, key, val):
        """
        Set to self with the dot-separated key.
        """
        tokens = key.split('.', 1)
        fkey = tokens[0]
        if len(tokens) == 2:
            self[fkey]._set_through(tokens[1], val)
        else:
            self[fkey] = val

    def __init__(self, _defdict=None, *args, **kw):
        """
        Assign default values to self after initiated.

        @keyword _defdict: customized defdict; internal use only.
        @type _defdict: dict
        """
        super(CaseInfo, self).__init__(*args, **kw)
        # customize defdict.
        if _defdict is None:
            defdict = self.defdict
        else:
            defdict = dict(self.defdict)
            defdict.update(_defdict)
        # parse first hierarchy to form key groups.
        keygrp = dict()
        for key in defdict.keys():
            if key is None or key == '':
                continue
            tokens = key.split('.', 1)
            if len(tokens) == 2:
                fkey, rkey = tokens
                keygrp.setdefault(fkey, dict())[rkey] = defdict[key]
            else:
                fkey = tokens[0]
                keygrp[fkey] = defdict[fkey]
        # set up first layer keys recursively.
        for fkey in keygrp.keys():
            data = keygrp[fkey]
            if isinstance(data, dict):
                self[fkey] = CaseInfo(_defdict=data)
            elif isinstance(data, type):
                try:
                    self[fkey] = data()
                except TypeError:
                    self[fkey] = data
            else:
                self[fkey] = data


class HookList(list):
    """
    Hook container and invoker.

    @ivar cse: case object.
    @itype cse: solvcon.case.BaseCase
    """

    def __init__(self, cse, *args, **kw):
        self.cse = cse
        super(HookList, self).__init__(*args, **kw)

    def append(self, obj, **kw):
        """
        The object to be appended (the first and only argument) should be a 
        Hook object, but this method actually accept either a Hook type or an
        Anchor type.  The method will automatically create the necessary Hook
        object when detect acceptable type object passed as the first argument.

        All the keywords go to the creation of the Hook object if the first
        argument is a type.  If the first argument is an instantiated Hook
        object, the method accepts no keywords.

        @param obj: the hook object to be appended.
        @type obj: solvcon.hook.Hook
        """
        if isinstance(obj, type):
            if issubclass(obj, anchor.Anchor):
                kw['ankcls'] = obj
                obj = hook.Hook
            obj = obj(self.cse, **kw)
        else:
            assert len(kw) == 0
        super(HookList, self).append(obj)

    def __call__(self, method):
        """
        Invoke the specified method for each hook object.

        @param method: name of the method to run.
        @type method: str
        """
        runhooks = self
        if method == 'postloop':
            runhooks = reversed(runhooks)
        for hook in runhooks:
            getattr(hook, method)()

    def drop_anchor(self, svr):
        for hok in self:
            hok.drop_anchor(svr)

# vim: set ff=unix fenc=utf8 ft=python ai et sw=4 ts=4 tw=79:
