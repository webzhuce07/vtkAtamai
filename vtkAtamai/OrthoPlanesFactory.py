# =========================================================================
#
# Copyright (c) 2000 Atamai, Inc.
#
# Use, modification and redistribution of the software, in source or
# binary forms, are permitted provided that the following terms and
# conditions are met:
#
# 1) Redistribution of the source code, in verbatim or modified
#    form, must retain the above copyright notice, this license,
#    the following disclaimer, and any notices that refer to this
#    license and/or the following disclaimer.
#
# 2) Redistribution in binary form must include the above copyright
#    notice, a copy of this license and the following disclaimer
#    in the documentation or with other materials provided with the
#    distribution.
#
# 3) Modified copies of the source code must be clearly marked as such,
#    and must not be misrepresented as verbatim copies of the source code.
#
# THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE SOFTWARE "AS IS"
# WITHOUT EXPRESSED OR IMPLIED WARRANTY INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE.  IN NO EVENT SHALL ANY COPYRIGHT HOLDER OR OTHER PARTY WHO MAY
# MODIFY AND/OR REDISTRIBUTE THE SOFTWARE UNDER THE TERMS OF THIS LICENSE
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, LOSS OF DATA OR DATA BECOMING INACCURATE
# OR LOSS OF PROFIT OR BUSINESS INTERRUPTION) ARISING IN ANY WAY OUT OF
# THE USE OR INABILITY TO USE THE SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGES.
#
# =========================================================================

#
# This file represents a derivative work by Parallax Innovations Inc.
#

__rcs_info__ = {
    #
    #  Creation Information
    #
    'module_name': '$RCSfile: OrthoPlanesFactory.py,v $',
    'creator': 'David Gobbi <dgobbi@atamai.com>',
    'project': 'Atamai Surgical Planning',
    #
    #  Current Information
    #
    'author': '$Author: jeremy_gill $',
    'version': '$Revision: 1.2 $',
    'date': '$Date: 2006/06/06 16:59:29 $',
}
try:
    __version__ = __rcs_info__['version'].split(' ')[1]
except:
    __version__ = '0.0'

"""
OrthoPlanesFactory - three orthogonal slice planes through a volume

  The OrthoPlanesFactory draws three orthogonal texture-mapped slices
  through a 3D image data set.  It also provides interaction modes
  to allow you to manipulate the three planes.

Derived From:

  ActorFactory

See Also:

  SlicePlaneFactory

Initialization:

  OrthoPlanesFactory()

Public Methods:

  Specify the image volume:

    SetInputData(*imagedata*,*i*=0)   -- set a vtkImageData to slice through

    GetInput(*i*=0)               -- get input *i*

    AddInputData(*imagedata*)         -- add an input after the last input

    RemoveInput(*i*=0)            -- remove an input

    GetNumberOfInputs()           -- current number of inputs

  Change the display of the image:

    SetLookupTable(*table*,*i*=0) -- change the lookup table for image *i*

    GetLookupTable(*i*=0)         -- get the lookup table

    SetOpacity(*alpha*,*i*=0)     -- set the opacity of image *i*

    GetOpacity(*i*=0)             -- get the opacity

    SetVisibility(*yesno*, *i*=0, *renderer*=None) -- change visibility of
                                     image *i* in a specific renderer

    GetVisibility(*i*=0, *renderer*=None) -- get the visibility

    SetImageTransform(*axes*,*i*=0) -- set a world coords -> image coords
                                     transformation to be used when displaying
                                     the image

    GetImageTransform(*i*=0)        -- get the image transformation

    SetClippingPlanes(*planes*,*i*=0) -- clip the image before displaying it

    GetClippingPlanes(*i*=0)        -- get the image clipping planes

    SetDefaultOutlineColor(*rgb*)   -- set the default plane outline colour

Plane Guides (4 rectangles that surround image plane during B2 events):
    ActivatePlaneGuides()           -- turns on guides

    SetDefaultOutlineColor(*rgb*)   -- set the default plane outline colour

Interpolation:

    SetSliceInterpolate(*boolean*) -- interpolate while resampling (default on)

    SetTextureInterpolate(*boolean*) -- interpolate when texture mapping
                                        (default on)

  Access the slice planes individually:

    GetPlanes()              -- get a list of three SlicePlaneFactories

    GetPlane(*actor*,*renderer*) -- get the SlicePlaneFactory for a particular
                                  *actor* and *renderer*, or None if *actor*
                                  not found


"""


#======================================
import ActorFactory
import SlicePlaneFactory
import PlaneIntersectionsFactory
import PlaneGuideFactory
import math
import vtk
import logging

#======================================


class OrthoPlanesFactory(ActorFactory.ActorFactory):

    def __init__(self):
        ActorFactory.ActorFactory.__init__(self)

        self._Inputs = {}
        self._LookupTables = {}
        self._Planes = []
        self._Plane = None    # currently picked plane
        self.cursor = None

        for i in range(3):
            plane = self.MakeSlicePlaneFactory()
            plane.RestrictPlaneToVolumeOn()
            self._Planes.append(plane)
            self.AddChild(plane)
            plane._Transform = self._Transform

        self._Intersections = self.MakePlaneIntersectionsFactory()
        ## self._Intersections.GetProperties().SetColor(1, 0, 0)
        self._Intersections.SetPlanes(self._Planes)
        self.AddChild(self._Intersections)

        self._PlaneGuides = PlaneGuideFactory.PlaneGuideFactory()
        self._PlaneGuides.SetOpacity(0.35)
        self._PlaneGuides.SetVisibility(0)

        self._PushColor = [0, 1, 0]
        self._RotateColor = [1, 0, 0]
        self._SpinColor = [0, 1, 1]

        self._DefaultOutlineColor = [1.0, 0.0, 1.0]  # [0.1843,0.3098,0.3098]

        for plane in self._Planes:
            plane.OutlineOn()
            plane.SetOutlineColor(self._DefaultOutlineColor)

        self.BindEvent("<ButtonPress>", self.DoStartAction)
        self.BindEvent("<ButtonRelease>", self.DoEndAction)
        self.BindEvent("<Motion>", self.DoAction)
        self.BindEvent("<B1-ButtonPress>", self.DoResetPlanes)
        self.BindEvent("<B2-ButtonPress>", self.DoResetPlanes)
        self.BindEvent("<B3-ButtonPress>", self.DoResetPlanes)

    def tearDown(self):
        ActorFactory.ActorFactory.tearDown(self)

        self._Planes = []
        self._Intersections = None
        self._PlaneGuides = None

    def ActivatePlaneGuides(self):
        self.AddChild(self._PlaneGuides)

    def MakeSlicePlaneFactory(self):
        return SlicePlaneFactory.SlicePlaneFactory()

    def MakePlaneIntersectionsFactory(self):
        return PlaneIntersectionsFactory.PlaneIntersectionsFactory()

    def DoResetPlanes(self, event):
        self._Transform.Identity()
        self.Modified()

    def DoStartAction(self, event):
        self._Plane = None
        for plane in self._Planes:
            if event.actor in plane.GetActors(event.renderer):
                self._LastX = event.x
                self._LastY = event.y
                self._Plane = plane
                break

        if self._Plane is None:
            return

        self._PlaneGuides.SetPlane(self._Plane)
        self._PlaneGuides.SetVisibility(1)

        # just set the action to 'push' if the view is a 2D view
        if event.renderer.GetActiveCamera().GetParallelProjection():
            self.__UserAction = 'Push'

            # propagate the event to the slice plane itself
            self._Plane.SetUserAction('Push')
            self._Plane.DoStartAction(event)

            return

        renderer = event.renderer

        # find intersection of viewing ray from LastX,LastY with the plane
        # in world coordinates
        wx, wy, wz = self._Plane.IntersectWithViewRay(self._LastX,
                                                      self._LastY,
                                                      renderer)

        # transform back to local coords of SlicePlaneFactory
        trans = self._Transform.GetInverse()
        lx, ly, lz = trans.TransformPoint(wx, wy, wz)

        ux, uy, uz = self._Plane.GetVector1()
        vx, vy, vz = self._Plane.GetVector2()
        ox, oy, oz = self._Plane.GetOrigin()
        us = self._Plane.GetSize1()
        vs = self._Plane.GetSize2()

        # use dot-product to convert to 2D X,Y values between [0,1]
        X = ((lx - ox) * ux + (ly - oy) * uy + (lz - oz) * uz) / us
        Y = ((lx - ox) * vx + (ly - oy) * vy + (lz - oz) * vz) / vs

        # divide plane into three zones for different user interactions:
        # four corns  -- spin around plane normal at ortho center
        # four edges  -- rotate around one of the plane axes at ortho center
        # center area -- push

        if ((X < 0.05 or X > 0.95) and (Y < 0.05 or Y > 0.95)):
            self.__UserAction = 'Spin'
        elif (X < 0.05 or X > 0.95):
            self.__UserAction = 'Rotate'
            self.__RotateAxis = (vx, vy, vz)
            self.__RadiusVector = (ux, uy, uz)
        elif (Y < 0.05 or Y > 0.95):
            self.__UserAction = 'Rotate'
            self.__RotateAxis = (ux, uy, uz)
            self.__RadiusVector = (vx, vy, vz)
        else:
            self.__UserAction = 'Push'

        # Make Plane guides visible
        if self.__UserAction == 'Push':
            self._PlaneGuides.SetColor(self._PushColor)
        elif self.__UserAction == 'Rotate':
            self._PlaneGuides.SetColor(self._RotateColor)
        elif self.__UserAction == 'Spin':
            self._PlaneGuides.SetColor(self._SpinColor)
        else:
            logging.error('Unknown action:', self.__UserAction)

        # propagate the event to the slice plane itself
        self._Plane.SetUserAction(self.__UserAction)
        self._Plane.DoStartAction(event)

        self.Modified()

    def DoEndAction(self, event):
        self.DoEndAction2(event)
        self.Modified()

    def DoEndAction2(self, event):
        """Body of DoEndAction() method

        This second call exists to allow inheritance to hook actions before a ModifiedEvent is posted"""
        if self._Plane:
            self._PlaneGuides.SetVisibility(0)
            self._Plane.DoEndAction(event)
            self._Plane = None

        self.__UserAction = None
        self.__RotateAxis = None
        self.__RadiusVector = None

    def DoAction(self, event):

        if (self._Plane == None):
            return
        if self.__UserAction == 'Push':
            self.DoPush(event)
        elif self.__UserAction == 'Spin':
            self.DoSpin(event)
        elif self.__UserAction == 'Rotate':
            self.DoRotation(event)
        else:
            pass

    def DoSpin(self, event):
        if (self._Plane == None):
            return

        renderer = event.renderer

        # find intersection of viewing ray from LastX,LastY with the plane
        lx, ly, lz = self._Plane.IntersectWithViewRay(self._LastX,
                                                      self._LastY,
                                                      renderer)

        # new intersection
        nx, ny, nz = self._Plane.IntersectWithViewRay(event.x,
                                                      event.y,
                                                      renderer)

        # mouse motion vector, in world coords
        dx, dy, dz = (nx - lx, ny - ly, nz - lz)

        # ortho Center and plane normal before transform
        center = self.GetOrthoCenter()
        normal = self._Plane.GetNormal()

        # after transform
        transform = self._Transform

        wc = transform.TransformPoint(center)
        wn = transform.TransformNormal(normal)

        # radius vector (from Ortho Center to cursor position)
        rv = (lx - wc[0], ly - wc[1], lz - wc[2])

        # distance between Ortho Center and cursor location
        rs = math.sqrt(rv[0] * rv[0] + rv[1] * rv[1] + rv[2] * rv[2])

        # normalize radius vector
        rv = [rv[0] / rs, rv[1] / rs, rv[2] / rs]

        # spin direction
        wn_cross_rv = (wn[1] * rv[2] - wn[2] * rv[1],
                       wn[2] * rv[0] - wn[0] * rv[2],
                       wn[0] * rv[1] - wn[1] * rv[0])

        # spin angle
        dw = 57.2957804904 * (dx * wn_cross_rv[0] +
                              dy * wn_cross_rv[1] +
                              dz * wn_cross_rv[2]) / rs

        # Translate the OrthoPlanes Center to origin of world coords
        transform.PostMultiply()
        transform.Translate(-center[0], -center[1], -center[2])

        # Rotate around plane normal
        transform.RotateWXYZ(dw, wn[0], wn[1], wn[2])

        # Translate back
        transform.Translate(center[0], center[1], center[2])

        self._LastX = event.x
        self._LastY = event.y

        # JDG added this
        self._dw = dw

        self.Modified()

    def DoRotation(self, event):
        if self._Plane is None:
            return

        renderer = event.renderer
        camera = renderer.GetActiveCamera()

        # find intersection of viewing ray from LastX,LastY with the plane
        lx, ly, lz = self._Plane.IntersectWithViewRay(self._LastX,
                                                      self._LastY,
                                                      renderer)

        # find depth-buffer value for intersection point
        renderer.SetWorldPoint(lx, ly, lz, 1.0)
        renderer.WorldToDisplay()
        z = renderer.GetDisplayPoint()[2]

        # and use it to find the world coords of the current x,y coord
        # (i.e. the mouse moves solely in x,y plane)
        renderer.SetDisplayPoint(event.x, event.y, z)
        renderer.DisplayToWorld()
        wx, wy, wz, w = renderer.GetWorldPoint()
        wx, wy, wz = (wx / w, wy / w, wz / w)

        # mouse motion vector, in world coords
        dx, dy, dz = (wx - lx, wy - ly, wz - lz)

        # ortho Center before transform
        center = self.GetOrthoCenter()

        # after transform
        transform = self._Transform
        wc = transform.TransformPoint(center)                # ortho center
        ra = transform.TransformVector(self.__RotateAxis)    # rotate axis
        rv = transform.TransformVector(self.__RadiusVector)  # radius vector

        # radius of the rotating circle of the picked point
        radius = abs(rv[0] * (lx - wc[0]) +
                     rv[1] * (ly - wc[1]) +
                     rv[2] * (lz - wc[2]))

        # rotate direction ra_cross_rv
        rd = (ra[1] * rv[2] - ra[2] * rv[1],
              ra[2] * rv[0] - ra[0] * rv[2],
              ra[0] * rv[1] - ra[1] * rv[0])

        # view normal
        vnx, vny, vnz = camera.GetViewPlaneNormal()

        # direction cosin between rotating direction and view normal
        rd_dot_vn = rd[0] * vnx + rd[1] * vny + rd[2] * vnz

        # 'push' plan edge when mouse move away from plan center
        # 'pull' plan edge when mouse move toward plan center
        dw = 57.28578 * \
            (dx * rv[0] + dy * rv[1] + dz * rv[2]) / radius * (-rd_dot_vn)

        # Translate the OrthoPlanes Ceter to origin of world coords
        transform.PostMultiply()
        transform.Translate(-center[0], -center[1], -center[2])

        # Rotate around rotation axis in the plane
        transform.RotateWXYZ(dw, ra[0], ra[1], ra[2])

        # Translate back
        transform.Translate(center[0], center[1], center[2])

        self._LastX = event.x
        self._LastY = event.y

        # JDG added this
        self._dw = dw

        self.Modified()

    def DoPush(self, event):
        if self._Plane:
            self._Plane.DoPush(event)
        self.Modified()

    def GetPlanes(self):
        return self._Planes

    def GetAxialPlane(self):
        return self._Planes[0]

    def GetCoronalPlane(self):
        return self._Planes[1]

    def GetSagittalPlane(self):
        return self._Planes[2]

    def GetPlane(self, actor, renderer=None):
        if (renderer != None):
            renderers = (renderer,)
        else:
            renderers = self._Renderers
        for renderer in renderers:
            for plane in self._Planes:
                if actor in plane.GetActors(renderer):
                    return plane

    def AddInputData(self, input, name=None):

        # this change permits orthoplanes to be named - fallback is to use a
        # numerical index
        if name is None:
            name = len(self._Inputs)

        while name in self._Inputs:
            name += 1

        self._Inputs[name] = input
        self._LookupTables[name] = None

        planes = self._Planes
        for plane in planes:
            plane.AddInputData(input, name)

        if name == 0:
            planes[0].SetPlaneOrientationToXY()
            planes[1].SetPlaneOrientationToZX()
            planes[2].SetPlaneOrientationToYZ()

        for plane in planes:
            plane.GetPlane().Update()

        self.Modified()

        return name

    def RemoveInput(self, name=0):
        """w.RemoveInput(name)  -- remove a particular named input
        """

        if name not in self._Inputs:
            raise ValueError(
                "RemoveInput: the specified input '{}' does not exist".format(name))
            return

        for plane in self._Planes:
            plane.RemoveInput(name)

        del self._Inputs[name]
        del self._LookupTables[name]

        self.Modified()

    def SetInputData(self, input, name=0):

        planes = self._Planes

        if name not in self._Inputs:
            self.AddInputData(input, name)
            return

        self._Inputs[name] = input
        for plane in planes:
            plane.SetInputData(input, name)

        if name == 0:
            planes[0].SetPlaneOrientationToXY()
            planes[1].SetPlaneOrientationToZX()
            planes[2].SetPlaneOrientationToYZ()

        for plane in planes:
            plane.GetPlane().Update()

        self.Modified()

    def GetOrthoCenter(self):
        # find the intesection point of the planes:
        # this is done by solving the three plane equations
        planes = self._Planes
        ux, uy, uz = planes[0].GetNormal()
        vx, vy, vz = planes[1].GetNormal()
        wx, wy, wz = planes[2].GetNormal()

        ax, ay, az = planes[0].GetOrigin()
        bx, by, bz = planes[1].GetOrigin()
        cx, cy, cz = planes[2].GetOrigin()

        a = ux * ax + uy * ay + uz * az
        b = vx * bx + vy * by + vz * bz
        c = wx * cx + wy * cy + wz * cz

        matrix = vtk.vtkMatrix4x4()
        matrix.DeepCopy((
            ux, uy, uz, 0, vx, vy, vz, 0, wx, wy, wz, 0, 0, 0, 0, 1))
        matrix.Invert()
        x, y, z, w = matrix.MultiplyPoint((a, b, c, 0))

        return (x, y, z)

    def SetOrthoCenter(self, *center):
        # set the intersection point of the three planes
        if len(center) == 1:
            center = center[0]

        for plane in self._Planes:
            origin = plane.GetOrigin()
            normal = plane.GetNormal()

            d = ((center[0] - origin[0]) * normal[0] +
                 (center[1] - origin[1]) * normal[1] +
                 (center[2] - origin[2]) * normal[2])

            plane.Push(d)

    def GetInput(self, i=0):

        if i in self._Inputs:
            return self._Inputs[i]
        else:
            return None

    def GetNumberOfInputs(self):
        return len(self._Inputs)

    def SetLookupTable(self, table, name=0):

        self._LookupTables[name] = table
        for plane in self._Planes:
            plane.SetLookupTable(table, name)

        self.Modified()

    def GetLookupTable(self, name=0):
        return self._LookupTables[name]

    def SetOpacity(self, alpha, name=0):
        for plane in self._Planes:
            plane.SetOpacity(alpha, name)

    def GetOpacity(self, name=0):
        return self._Planes[0].GetOpacity(name)

    def SetImageTransform(self, transform, name=0):
        for plane in self._Planes:
            plane.SetImageTransform(transform, name)
        self.Modified()

    def GetImageTransform(self, name=0):
        return self._Planes[0].GetImageTransform(name)

    def SetClippingPlanes(self, i, clippingPlanes=None):
        if (clippingPlanes == None):
            clippingPlanes = i
            i = 0
        for plane in self._Planes:
            plane.SetClippingPlanes(i, clippingPlanes)

    def GetClippingPlanes(self, i=0):
        return self._Planes[0].GetClippingPlanes(i)

    def SetSliceInterpolate(self, val):
        for plane in self._Planes:
            plane.SetSliceInterpolate(val)
        self.Modified()

    def GetSliceInterpolate(self):
        return self._Planes[0].GetSliceInterpolate()

    def SliceInterpolateOn(self):
        self.SetSliceInterpolate(1)

    def SliceInterpolateOff(self):
        self.SetSliceInterpolate(0)

    def SetTextureInterpolate(self, val):
        for plane in self._Planes:
            plane.SetTextureInterpolate(val)
        self.Modified()

    def GetTextureInterpolate(self):
        return self._Planes[0].GetTextureInterpolate()

    def TextureInterpolateOn(self):
        self.SetTextureInterpolate(1)

    def TextureInterpolateOff(self):
        self.SetTextureInterpolate(0)

    def GetPlaneEquations(self):
        planes = vtk.vtkPlaneCollection()
        for plane in self._Planes:
            planes.AddItem(plane.GetPlaneEquation())
        return planes

    def OrthoPlanesReset(self):
        # same as DoResetPlanes, but callable
        self._Transform.Identity()

    def SetIntersectionsOnOff(self, toggle):
        onoff = int(toggle)
        self._Intersections.SetVisibility(toggle)
        for plane in self._Planes:
            if onoff == 1:
                plane.OutlineOn()
            else:
                plane.OutlineOff()
        self.Modified()

    def IntersectionsOn(self):
        # Set 1 to the visibility of the intersections of ortho planes
        self._Intersections.SetVisibility(1)
        self.Modified()

    def IntersectionsOff(self):
        # Set 0 to the visibility of the intersections of orthos planes
        self._Intersections.SetVisibility(0)
        self.Modified()

    def SetDefaultOutlineColor(self, color):
        self._DefaultOutlineColor = color
        for plane in self._Planes:
            plane.SetDefaultOutlineColor(color)
