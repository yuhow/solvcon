# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2009 by Yung-Yu Chen.  See LICENSE.txt for terms of usage.

"""Unstructured mesh definition."""

from numpy import array
from .dependency import FortranType

# metadata for unstructured mesh.
elemtype = array([
    # index, dim, node, edge, face,    name
    [     0,   0,    1,    0,    0, ], # node/point/vertex
    [     1,   1,    2,    0,    0, ], # line/edge
    [     2,   2,    4,    4,    0, ], # quadrilateral
    [     3,   2,    3,    3,    0, ], # triangle
    [     4,   3,    8,    8,    6, ], # hexahedron/brick
    [     5,   3,    4,    4,    4, ], # tetrahedron
    [     6,   3,    6,    9,    5, ], # prism/wedge
    [     7,   3,    5,    8,    5, ], # pyramid
], dtype='int32')
MAX_FCNND = elemtype[elemtype[:,1]<3,2].max()
MAX_CLNND = elemtype[:,2].max()
MAX_CLNFC = max(elemtype[elemtype[:,1]==2,3].max(),
                elemtype[elemtype[:,1]==3,4].max())

class BlockShape(FortranType):
    """
    The shape of a block.
    """

    _fortran_name_ = 'block'
    from ctypes import c_int
    _fields_ = [
        ('ndim', c_int),
        ('fcmnd', c_int),
        ('clmnd', c_int),
        ('clmfc', c_int),
        ('nnode', c_int), ('nface', c_int), ('ncell', c_int),
        ('nbound', c_int),
        ('ngstnode', c_int), ('ngstface', c_int), ('ngstcell', c_int),
    ]
    del c_int

    def __init__(self, *args, **kw):
        blk = kw.pop('blk', None)
        super(BlockShape, self).__init__(*args, **kw)
        if blk:
            for name, ft in self._fields_:
                val = getattr(blk, name, None)
                if val == None:
                    val = getattr(blk, name.upper(), None)
                setattr(self, name, val)

class Block(object):
    """
    Provide metric and connectivity information for unstructured-mesh block.
    In terms of APIs in the Block class, to build a block requires the
    following actions:
      1. build_interior: build up inner connectivity and call calc_metric to
         calculate metrics for interior meshes.
      2. build_boundary: build up information of boundary faces according to
         boundary conditions objects (BCs).  Also "patch" the block with
         "unspecified" BC for boundary faces without related BC objects.
      3. build_ghost: build up information for ghost cells.  Ghost cells is for
         treatment of boundary conditions in a solving code/logic.  The
         build-up includes create ghost entities (nodes, faces, and cells
         itself) and their connectivity and metrics.  The storage of interior
         meshed will be changed to make the storgae for both interior and ghost
         information contiguous.

    @note: Prefixes: nd = node, fc = face, cl = cell; gst = ghost; sh = shared.

    @ivar _fpdtype: dtype for the floating point data in the block instance.
    @ivar blkn: serial number of the block.
    @ivar bclist: list of associated BC objects.
    @ivar bndfcs: list of BC faces, contains BC face index and BC class serial
        number, respectively.  The type number definition follows Nasa 2D CESE 
        code.
    @ivar grpnames: list of names of cell groups.
    @ivar ndcrd: Node croodinate data.
    @ivar fccnd: Central coordinates of face.
    @ivar fcnml: Unit-normal vector of face.
    @ivar fcara: Area of face.
    @ivar clcnd: Central coordinates of cell.
    @ivar clvol: Volume of cell.
    @ivar fctpn: Type of face.
    @ivar cltpn: Type of cell.
    @ivar clgrp: Group index of cell.
    @ivar fcnds: List of nodes in face; arr[:,0] for the number.
    @ivar fccls: Related cells for each face, contains belong, neibor (ghost as
        negative), neiblk, and neibcl (cell index in neighboring block), 
        respectively.
    @ivar clnds: List of nodes in cell; arr[:,0] for the number.
    @ivar clfcs: List of faces in cell; arr[:,0] for the number.
    """

    FCMND = MAX_FCNND
    CLMND = MAX_CLNND
    CLMFC = MAX_CLNFC

    def __init__(self, *args, **kw):
        """
        Initialization.

        @keyword fpdtype: dtype for the floating point data.
        @keyword ndim: spatial dimension.
        @keyword nnode: number of nodes.
        @keyword nface: number of faces.
        @keyword ncell: number of cells.
        @keyword nbound: number of BC faces.
        """
        import numpy
        from numpy import empty
        from .conf import env
        # get parameters.
        self._fpdtype = kw.pop('fpdtype', env.fpdtype)
        self._fpdtype = env.fpdtype if self._fpdtype==None else self._fpdtype
        ndim = kw.setdefault('ndim', 0)
        nnode = kw.setdefault('nnode', 0)
        nface = kw.setdefault('nface', 0)
        ncell = kw.setdefault('ncell', 0)
        nbound = kw.setdefault('nbound', 0)
        # serial number of the block.
        self.blkn = None
        # boundary conditions and boundary faces information.
        self.bclist = list()
        self.bndfcs = empty((nbound, 2), dtype='int32')
        # group names.
        self.grpnames = list()
        # interior data.
        ## metrics.
        self.ndcrd = empty((nnode, ndim), dtype=self.fpdtype)
        self.fccnd = empty((nface, ndim), dtype=self.fpdtype)
        self.fcnml = empty((nface, ndim), dtype=self.fpdtype)
        self.fcara = empty(nface, dtype=self.fpdtype)
        self.clcnd = empty((ncell, ndim), dtype=self.fpdtype)
        self.clvol = empty(ncell, dtype=self.fpdtype)
        ## type data.
        self.fctpn = empty(nface, dtype='int32')
        self.cltpn = empty(ncell, dtype='int32')
        self.clgrp = empty(ncell, dtype='int32')
        self.clgrp.fill(-1) # every cell should be in 0-th group by default.
        ## connectivities.
        self.fcnds = empty((nface, self.FCMND+1), dtype='int32')
        self.fccls = empty((nface, 4), dtype='int32')
        self.clnds = empty((ncell, self.CLMND+1), dtype='int32')
        self.clfcs = empty((ncell, self.CLMFC+1), dtype='int32')
        for arr in self.clnds, self.clfcs, self.fcnds, self.fccls:
            arr.fill(-1)
        # ghost data.
        ## metrics. (placeholder)
        self.gstndcrd = empty((0, ndim), dtype=self.fpdtype)
        self.gstfccnd = empty((0, ndim), dtype=self.fpdtype)
        self.gstfcnml = empty((0, ndim), dtype=self.fpdtype)
        self.gstfcara = empty(0, dtype=self.fpdtype)
        self.gstclcnd = empty((0, ndim), dtype=self.fpdtype)
        self.gstclvol = empty(0, dtype=self.fpdtype)
        ## type data. (placeholder)
        self.gstfctpn = empty(0, dtype='int32')
        self.gstcltpn = empty(0, dtype='int32')
        self.gstclgrp = empty(0, dtype='int32')
        ## connectivities. (placeholder)
        self.gstfcnds = empty((0, self.FCMND+1), dtype='int32')
        self.gstfccls = empty((0, 4), dtype='int32')
        self.gstclnds = empty((0, self.CLMND+1), dtype='int32')
        self.gstclfcs = empty((0, self.CLMFC+1), dtype='int32')
        # shared (by interior/real and ghost).
        ## metrics. (placeholder)
        self.shndcrd = empty((0, ndim), dtype=self.fpdtype)
        self.shfccnd = empty((0, ndim), dtype=self.fpdtype)
        self.shfcnml = empty((0, ndim), dtype=self.fpdtype)
        self.shfcara = empty(0, dtype=self.fpdtype)
        self.shclcnd = empty((0, ndim), dtype=self.fpdtype)
        self.shclvol = empty(0, dtype=self.fpdtype)
        ## type data. (placeholder)
        self.shfctpn = empty(0, dtype='int32')
        self.shcltpn = empty(0, dtype='int32')
        self.shclgrp = empty(0, dtype='int32')
        ## connectivities. (placeholder)
        self.shfcnds = empty((0, self.FCMND+1), dtype='int32')
        self.shfccls = empty((0, 4), dtype='int32')
        self.shclnds = empty((0, self.CLMND+1), dtype='int32')
        self.shclfcs = empty((0, self.CLMFC+1), dtype='int32')
        # keep initialization sequence.
        super(Block, self).__init__()

    def __str__(self):
        return ', '.join([
            '[Block (%dD): %d nodes'%(self.ndim, self.nnode),
            '%d faces (%d BC)'%(self.nface, self.nbound),
            '%d cells]'%self.ncell
        ])

    @property
    def fpdtype(self):
        import numpy
        _fpdtype = self._fpdtype
        if isinstance(_fpdtype, str):
            return getattr(numpy, _fpdtype)
        else:
            return self._fpdtype
    @property
    def fpdtypestr(self):
        from .dependency import str_of
        return str_of(self.fpdtype)
    @property
    def fpptr(self):
        from .dependency import pointer_of
        return pointer_of(self.fpdtype)
    @property
    def _clib_solvcon(self):
        from .dependency import _clib_solvcon_of
        return _clib_solvcon_of(self.fpdtype)

    @property
    def ndim(self):
        return self.ndcrd.shape[1]
    @property
    def nnode(self):
        return self.ndcrd.shape[0]
    @property
    def nface(self):
        return self.fcnds.shape[0]
    @property
    def ncell(self):
        return self.clnds.shape[0]
    @property
    def nbound(self):
        return self.bndfcs.shape[0]
    @property
    def ngstnode(self):
        return self.gstndcrd.shape[0]
    @property
    def ngstface(self):
        return self.gstfcnds.shape[0]
    @property
    def ngstcell(self):
        return self.gstclnds.shape[0]

    def bind(self):
        for bc in self.bclist:
            bc.bind()
    def unbind(self):
        for bc in self.bclist:
            bc.unbind()

    def create_shape(self):
        """
        @return: the shape of this block.
        @rtype: BlockShape
        """
        return BlockShape(blk=self)

    def calc_metric(self):
        """
        Calculate metrics including normal vector and area of faces, and
        centroid coordinates and volume of cells.

        @return: nothing.
        """
        from ctypes import byref
        from .dependency import intptr
        # call the subroutine.
        fpptr = self.fpptr
        msh = self.create_shape()
        self._clib_solvcon.calc_metric_(
            # input.
            byref(msh),
            self.ndcrd.ctypes.data_as(self.fpptr),
            self.fccls.ctypes.data_as(intptr),
            self.clnds.ctypes.data_as(intptr),
            self.clfcs.ctypes.data_as(intptr),
            # output/input.
            self.fcnds.ctypes.data_as(intptr),
            self.fccnd.ctypes.data_as(fpptr),
            self.fcnml.ctypes.data_as(fpptr),
            self.fcara.ctypes.data_as(fpptr),
            self.clcnd.ctypes.data_as(fpptr),
            self.clvol.ctypes.data_as(fpptr),
        )

    def build_interior(self):
        """
        Build all remaining connectivity information out of cell node
        definition, and calculate metric.

        This method alters content in self object.

        @return: nothing.
        """
        from numpy import empty
        from ctypes import byref, c_int
        from .dependency import intptr
        # prepare to build connectivity: calculate max number of faces.
        max_nfc = 0
        for sig in elemtype[1:2]:   # 1D cells.
            max_nfc += (self.cltpn == sig[0]).sum()*sig[2]
        for sig in elemtype[2:4]:   # 2D cells.
            max_nfc += (self.cltpn == sig[0]).sum()*sig[3]
        for sig in elemtype[4:]:    # 3D cells.
            max_nfc += (self.cltpn == sig[0]).sum()*sig[4]
        # build connectivity information: get face definition from node list 
        # of cells.
        nface = c_int(0)
        clfcs = empty((self.ncell, self.CLMFC+1), dtype='int32')
        fctpn = empty(max_nfc, dtype='int32')
        fcnds = empty((max_nfc, self.FCMND+1), dtype='int32')
        fccls = empty((max_nfc, 4), dtype='int32')
        for arr in clfcs, fcnds, fccls:
            arr.fill(-1)
        ## call the subroutine.
        self._clib_solvcon.get_faces_from_cells_(
            # input.
            byref(c_int(self.nnode)),
            byref(c_int(self.ncell)),
            byref(c_int(max_nfc)),
            byref(c_int(self.CLMND)),
            byref(c_int(self.CLMFC)),
            byref(c_int(self.FCMND)),
            self.cltpn.ctypes.data_as(intptr),
            self.clnds.ctypes.data_as(intptr),
            # output.
            byref(nface),
            clfcs.ctypes.data_as(intptr),
            fctpn.ctypes.data_as(intptr),
            fcnds.ctypes.data_as(intptr),
            fccls.ctypes.data_as(intptr),
        )
        ## shuffle the result.
        nface = nface.value
        clfcs = clfcs[:nface,:]
        fctpn = fctpn[:nface]
        fcnds = fcnds[:nface,:]
        fccls = fccls[:nface,:]
        # check for initialization of information for faces.
        if self.nface != nface:
            # connectivity, used in this method.
            self.fctpn = empty(nface, dtype='int32')
            self.fcnds = empty((nface, self.FCMND+1), dtype='int32')
            self.fccls = empty((nface, 4), dtype='int32')
            self.fccnd = empty((nface, self.ndim), dtype=self.fpdtype)
            self.fcnml = empty((nface, self.ndim), dtype=self.fpdtype)
            self.fcara = empty(nface, dtype=self.fpdtype)
        # assign extracted data to block.
        self.clfcs[:,:] = clfcs[:,:]
        self.fctpn[:] = fctpn[:]
        self.fcnds[:,:] = fcnds[:,:]
        self.fccls[:,:] = fccls[:,:]
        # calculate metric information.
        self.calc_metric()

    def build_boundary(self, unspec_type=None, unspec_name="unspecified"):
        """
        Build boundary faces according to face connectivity.  If a face belongs
        to only one cell (i.e., has no neighboring cell), it is regarded as a
        boundary face.

        This method alters content in self object.

        @keyword unspec_type: BC type for the unspecified boundary faces.
            The default is solvcon.boundcond.unspecified.
        @type unspec_type: solvcon.boundcond.BC
        @keyword unspec_name: name for the unspecified BC.
        @type unspec_name: str

        @return: nothing.
        """
        from numpy import arange, empty
        from .boundcond import bctregy
        if unspec_type == None:
            unspec_type = bctregy.unspecified
        # count all possible boundary faces.
        slct = self.fccls[:,1] < 0
        nbound = slct.sum()
        allfacn = arange(self.nface, dtype='int32')[slct]
        # collect type definition from bclist.
        specified = empty(nbound, dtype='bool')
        specified.fill(False)
        bndfcs = empty((nbound, 2), dtype='int32')
        ibfc = 0
        for bc in self.bclist:
            # save face indices and type number to array.
            bndfcs[ibfc:ibfc+len(bc),0] = bc.facn[:,0]
            bndfcs[ibfc:ibfc+len(bc),1] = bc.sern
            # save bndfc indices back to bc object.
            bc.facn[:,1] = arange(ibfc,ibfc+len(bc))
            # mark specified indices.
            slct = allfacn.searchsorted(bc.facn[:,0])
            specified[slct] = True
            # advance counter.
            ibfc += len(bc)
        # collect unspecified boundary faces.
        leftfcs = allfacn[specified == False]
        if leftfcs.shape[0] != 0:
            # add unspecified boundary faces to an additional BC object.
            bc = unspec_type()
            bc.name = unspec_name
            bc.sern = len(self.bclist)
            bc.blk = self
            bc.facn = empty((len(leftfcs),3), dtype='int32')
            bc.facn[:,0] = leftfcs[:]
            bc.facn[:,1] = arange(ibfc,ibfc+len(bc))
            self.bclist.append(bc)
            bndfcs[ibfc:,0] = bc.facn[:,0]
            bndfcs[ibfc:,1] = bc.sern
        # finish, save array to block object.
        self.bndfcs = bndfcs

    def build_ghost(self):
        """
        Build data for ghost cells and related information.

        This method alters content in self object.

        @return: nothing.
        """
        from ctypes import byref
        from numpy import arange
        from .dependency import intptr
        # initialize data structure (arrays) for ghost information.
        ngstnode, ngstface, ngstcell = self._count_ghost()
        self._init_shared(ngstnode, ngstface, ngstcell)
        self._assign_ghost(ngstnode, ngstface, ngstcell)
        self._reassign_interior(ngstnode, ngstface, ngstcell)
        # build ghost information, including connectivities and metrics.
        fpptr = self.fpptr
        msh = self.create_shape()
        self._clib_solvcon.build_ghost_(
            # meta data.
            byref(msh),
            self.bndfcs.ctypes.data_as(intptr),
            self.shfctpn.ctypes.data_as(intptr),
            self.shcltpn.ctypes.data_as(intptr),
            self.shclgrp.ctypes.data_as(intptr),
            # connectivity.
            self.shfcnds.ctypes.data_as(intptr),
            self.shfccls.ctypes.data_as(intptr),
            self.shclnds.ctypes.data_as(intptr),
            self.shclfcs.ctypes.data_as(intptr),
            # geometry.
            self.shndcrd.ctypes.data_as(fpptr),
            self.shfccnd.ctypes.data_as(fpptr),
            self.shfcnml.ctypes.data_as(fpptr),
            self.shfcara.ctypes.data_as(fpptr),
            self.shclcnd.ctypes.data_as(fpptr),
            self.shclvol.ctypes.data_as(fpptr),
        )

    def _count_ghost(self):
        """
        Count number of ghost entities.  Number of nodes, faces, and cells for
        ghost can be determined according to boundary connectivities.

        Nubmer of ghost cells is exactly the number of boundary faces.

        Number of exterior faces for ghost cells is the total number of faces of
        ghost cells minus the number of boundary faces (which is shared between
        ghost cells and adjacent interior cells).

        Number of exterior nodes for ghost cells is the total number of nodes of 
        ghost cells minus the total number of nodes of boundary faces.

        @return: node, face, and cell number for ghost.
        @rtype: tuple
        """
        bfcs = self.bndfcs[:,0]
        bcls = self.fccls[bfcs,0]    # interior cells next to boundary.
        # count/get the number of total ghost faces.
        ngstcell = self.nbound
        # count the number of total ghost faces.
        gstcltpn = self.cltpn[bcls]
        ngstface = 0
        for thetype in elemtype[1:]:
            dim = thetype[1]
            nfc = thetype[1+dim]
            ncl = (gstcltpn==thetype[0]).sum()
            ngstface += (nfc-1)*ncl # only one concrete face for each ghost cell.
        # count the number of total ghost nodes.
        ngstnode = self.clnds[bcls,0].sum() - self.fcnds[bfcs,0].sum()
        # return result.
        return ngstnode, ngstface, ngstcell

    def _init_shared(self, ngstnode, ngstface, ngstcell):
        """
        Allocate arrays to stored data both for ghost and real/interior cells.
        
        This method alters content in self object.

        @param ngstnode: number of nodes for ghost cells.
        @type ngstnode: int
        @param ngstcell: number of faces for ghost cells.
        @type ngstface: int
        @param ngstcell: number of ghost cells.
        @type ngstcell: int
        @return: nothing.
        """
        from numpy import empty
        ndim = self.ndim
        nnode = self.nnode
        nface = self.nface
        ncell = self.ncell
        # shared metrics.
        self.shndcrd = empty((ngstnode+nnode, ndim), dtype=self.fpdtype)
        self.shfccnd = empty((ngstface+nface, ndim), dtype=self.fpdtype)
        self.shfcnml = empty((ngstface+nface,ndim), dtype=self.fpdtype)
        self.shfcara = empty(ngstface+nface, dtype=self.fpdtype)
        self.shclcnd = empty((ngstcell+ncell, ndim), dtype=self.fpdtype)
        self.shclvol = empty(ngstcell+ncell, dtype=self.fpdtype)
        # shared type data.
        self.shfctpn = empty(ngstface+nface, dtype='int32')
        self.shcltpn = empty(ngstcell+ncell, dtype='int32')
        # shared connectivities.
        self.shfcnds = empty((ngstface+nface, self.FCMND+1), dtype='int32')
        self.shfccls = empty((ngstface+nface, 4), dtype='int32')
        self.shclnds = empty((ngstcell+ncell, self.CLMND+1), dtype='int32')
        self.shclfcs = empty((ngstcell+ncell, self.CLMFC+1), dtype='int32')
        for arr in self.shclnds, self.shclfcs, self.shfcnds, self.shfccls:
            arr.fill(-1)
        # descriptive data.
        self.shclgrp = empty(ngstcell+ncell, dtype='int32')

    def _assign_ghost(self, ngstnode, ngstface, ngstcell):
        """
        Assign ghost arrays to lower portion of shared arrays.

        This method alters content in self object.

        @param ngstnode: number of nodes for ghost cells.
        @type ngstnode: int
        @param ngstcell: number of faces for ghost cells.
        @type ngstface: int
        @param ngstcell: number of ghost cells.
        @type ngstcell: int
        @return: nothing.
        """
        # ghost metrics.
        self.gstndcrd = self.shndcrd[ngstnode-1::-1,:]
        self.gstfccnd = self.shfccnd[ngstface-1::-1,:]
        self.gstfcnml = self.shfcnml[ngstface-1::-1,:]
        self.gstfcara = self.shfcara[ngstface-1::-1]
        self.gstclcnd = self.shclcnd[ngstcell-1::-1,:]
        self.gstclvol = self.shclvol[ngstcell-1::-1]
        # ghost type data.
        self.gstfctpn = self.shfctpn[ngstface-1::-1]
        self.gstcltpn = self.shcltpn[ngstcell-1::-1]
        # ghost connectivities.
        self.gstfcnds = self.shfcnds[ngstface-1::-1,:]
        self.gstfccls = self.shfccls[ngstface-1::-1,:]
        self.gstclnds = self.shclnds[ngstcell-1::-1,:]
        self.gstclfcs = self.shclfcs[ngstcell-1::-1,:]
        # descriptive data.
        self.gstclgrp = self.shclgrp[ngstcell-1::-1]

    def _reassign_interior(self, ngstnode, ngstface, ngstcell):
        """
        Reassign interior data stored in standalone ndarray object to upper
        portion of shared ndarray object.

        This method alters content in self object.

        @param ngstnode: number of nodes for ghost cells.
        @type ngstnode: int
        @param ngstcell: number of faces for ghost cells.
        @type ngstface: int
        @param ngstcell: number of ghost cells.
        @type ngstcell: int
        @return: nothing.
        """
        ndim = self.ndim
        nnode = self.nnode
        nface = self.nface
        ncell = self.ncell
        # reassign metrics.
        ## node coordinate.
        ndcrd = self.shndcrd[ngstnode:,:]
        ndcrd[:,:] = self.ndcrd[:,:]
        self.ndcrd = ndcrd
        ## face center coordinate.
        fccnd = self.shfccnd[ngstface:,:]
        fccnd[:,:] = self.fccnd[:,:]
        self.fccnd = fccnd
        ## face unit normal vector.
        fcnml = self.shfcnml[ngstface:,:]
        fcnml[:,:] = self.fcnml[:,:]
        self.fcnml = fcnml
        ## face area.
        fcara = self.shfcara[ngstface:]
        fcara[:] = self.fcara[:]
        self.fcara = fcara
        ## cell center coordinate.
        clcnd = self.shclcnd[ngstcell:,:]
        clcnd[:,:] = self.clcnd[:,:]
        self.clcnd = clcnd
        ## cell volume.
        clvol = self.shclvol[ngstcell:]
        clvol[:] = self.clvol[:]
        self.clvol = clvol
        # reassign type data.
        ## face type.
        fctpn = self.shfctpn[ngstface:]
        fctpn[:] = self.fctpn[:]
        self.fctpn = fctpn
        ## cell type.
        cltpn = self.shcltpn[ngstcell:]
        cltpn[:] = self.cltpn[:]
        self.cltpn = cltpn
        # reassign connectivities.
        ## nodes in faces.
        fcnds = self.shfcnds[ngstface:,:]
        fcnds[:,:] = self.fcnds[:,:]
        self.fcnds = fcnds
        ## cells between faces.
        fccls = self.shfccls[ngstface:,:]
        fccls[:,:] = self.fccls[:,:]
        self.fccls = fccls
        ## nodes in cells.
        clnds = self.shclnds[ngstcell:,:]
        clnds[:,:] = self.clnds[:,:]
        self.clnds = clnds
        ## faces around cells.
        clfcs = self.shclfcs[ngstcell:,:]
        clfcs[:,:] = self.clfcs[:,:]
        self.clfcs = clfcs
        # reassign descriptive.
        ## cell group.
        clgrp = self.shclgrp[ngstcell:]
        clgrp[:] = self.clgrp[:]
        self.clgrp = clgrp
