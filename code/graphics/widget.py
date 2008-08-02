#file: widget.py
#Copyright (C) 2008 FunnyMan3595
#This file is part of Endgame: Singularity.

#Endgame: Singularity is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#Endgame: Singularity is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Endgame: Singularity; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#This file contains the widget class.

import pygame
from Numeric import array

import g
import constants

def unmask(widget):
    """Causes the widget to exist above its parent's fade mask.  The widget's
       children will still be masked, unless they are unmasked themselves."""
    unmask_all(widget)
    widget.mask_children = True

def unmask_all(widget):
    """Causes the widget to exist above its parent's fade mask.  The widget's
       children will not be masked."""
    widget.self_mask = True
    widget.do_mask = lambda: None

def call_on_change(data_member, call_me, *args, **kwargs):
    """Creates a data member that sets another data member to a given value
       when changed."""
    def get(self):
        return getattr(self, data_member)

    def set(self, my_value):
        if data_member in self.__dict__:
            change = (my_value != self.__dict__[data_member])
        else:
            change = True

        if change:
            setattr(self, data_member, my_value)
            call_me(self, *args, **kwargs)

    return property(get, set)

def set_on_change(data_member, set_me, set_value = True):
    """Creates a data member that sets another data member to a given value
       when changed."""
    return call_on_change(data_member, setattr, set_me, set_value)

def causes_rebuild(data_member):
    """Creates a data member that sets needs_rebuild to True when changed."""
    return set_on_change(data_member, "needs_rebuild")

def causes_redraw(data_member):
    """Creates a data member that sets needs_redraw to True when changed."""
    return set_on_change(data_member, "needs_redraw")

def causes_full_redraw(data_member):
    """Creates a data member that sets needs_redraw to True when changed."""
    return set_on_change(data_member, "needs_full_redraw")

class Widget(object):
    """A Widget is a GUI element.  It can have one parent and any number of
       children."""

    def _propogate_redraw(self):
        if self.needs_redraw:
            target = self.parent
            while target:
                target._needs_redraw = self.needs_redraw
                target = target.parent

    needs_redraw = call_on_change("_needs_redraw", _propogate_redraw)

    def _propogate_full_redraw(self):
        if self._needs_full_redraw and not getattr(self, "needs_redraw", 0):
            self.needs_redraw = self._needs_full_redraw

    needs_full_redraw = call_on_change("_needs_full_redraw", 
                                       _propogate_full_redraw)

    def _propogate_rebuild(self):
        self.needs_redraw = self.needs_rebuild # Propagates if needed.

    needs_rebuild = call_on_change("_needs_rebuild", _propogate_rebuild)

    pos = causes_full_redraw("_pos")
    size = causes_rebuild("_size")
    anchor = causes_full_redraw("_anchor")
    children = causes_redraw("_children")
    visible = causes_redraw("_visible")

    def __init__(self, parent, pos, size, anchor = constants.TOP_LEFT):
        self.parent = parent
        self.pos = pos
        self.size = size
        self.anchor = anchor

        self.children = []

        # "It's a widget!"
        if self.parent:
            self.add_hooks()

        self.is_above_mask = False
        self.self_mask = False
        self.mask_children = False
        self.visible = True

        # Set automatically by other properties.
        #self.needs_rebuild = True
        #self.needs_redraw = True
        #self.needs_full_redraw = True

    def add_hooks(self):
        self.parent.children.append(self)
        # Won't trigger on the call from __init__, since there are no children
        # yet, but add_hooks may be explicitly called elsewhere to undo
        # remove_hooks.
        for child in self.children:
            child.add_hooks()

    def remove_hooks(self):
        self.parent.children.remove(self)
        for child in self.children:
            child.remove_hooks()

    def _parent_size(self):
        if self.parent == None:
            return g.screen_size
        else:
            return self.parent.real_size

    def _calc_size(self):
        """Internal method.  Calculates and returns the real size of this
           widget.

           Override to create a dynamically-sized widget."""
        parent_size = self._parent_size()
        size = list(self.size)
        for i in range(2):
            if size[i] > 0:
                size[i] = int(size[i] * g.screen_size[i])
            elif size[i] < 0:
                size[i] = int( (-size[i]) * parent_size[i] )

        return tuple(size)

    def get_real_size(self):
        """Returns the real size of this widget.

           To implement a dynamically-sized widget, override _calc_size, which
           will be called whenever the widget is rebuilt."""
        if self.needs_rebuild:
            self._real_size = self._calc_size()

        return self._real_size

    real_size = property(get_real_size)

    def get_real_pos(self):
        """Returns the real position of this widget on its parent."""
        vanchor, hanchor = self.anchor
        parent_size = self._parent_size()
        my_size = self.real_size

        if self.pos[0] >= 0:
            hpos = int(self.pos[0] * g.screen_size[0])
        else:
            hpos = - int(self.pos[0] * parent_size[0])

        if hanchor == constants.LEFT:
            pass
        elif hanchor == constants.CENTER:
            hpos -= my_size[0] // 2
        elif hanchor == constants.RIGHT:
            hpos -= my_size[0]

        if self.pos[1] >= 0:
            vpos = int(self.pos[1] * g.screen_size[1])
        else:
            vpos = - int(self.pos[1] * parent_size[1])

        if vanchor == constants.TOP:
            pass
        elif vanchor == constants.MID:
            vpos -= my_size[1] // 2
        elif vanchor == constants.BOTTOM:
            vpos -= my_size[1]

        return (hpos, vpos)

    real_pos = property(get_real_pos)

    def _make_collision_rect(self):
        """Creates and returns a collision rect for this widget."""
        pos = array(self.real_pos)
        if self.parent:
            pos += self.parent.collision_rect[:2]

        return pygame.sprite.Rect(pos, self.real_size)

    def is_over(self, position):
        return self.collision_rect.collidepoint(position)

    def remake_surfaces(self):
        """Recreates the surfaces that this widget will draw on."""
        size = self.real_size

        if self.parent != None:
            self.surface = pygame.Surface(size, 0, g.ALPHA)
            color = (0,0,0,0)
        else:
            self.surface = pygame.display.set_mode(size, g.fullscreen)
            color = (0,0,0,255)

        self.surface.fill( color )

        self.internal_surface = pygame.Surface(size, 0, g.ALPHA)
        self.internal_surface.fill( color )

    def rebuild(self):
        """Generic rebuild of a widget.  Recreates the surfaces, unsets
           needs_rebuild, and passes the rebuild on to the widget's
           children.

           Override to draw custom art for this widget.  Call this at the
           beginning of the overrided method."""
        self.remake_surfaces()
        self.needs_rebuild = False
        for child in self.children:
            child.needs_rebuild = True

        self.needs_redraw = True # Propagates.

    def redraw(self):
        """Handles redrawing a widget and its children.  Art specific to this 
           widget should be drawn by overriding rebuild, not redraw."""
        # If the widget's own image needs to be rebuilt, do it and mark the
        # widget as needing a redraw.
        if self.needs_rebuild:
            self.rebuild()

        # Redraw the widget.
        if self.needs_redraw:
            # Recalculate the widget's absolute position.
            self.collision_rect = self._make_collision_rect()

            # Clear the surface and draw the widget's image.
            self.surface.fill( (0,0,0,0) )
            self.surface.blit( self.internal_surface, (0,0) )

            # Draw the widget's children who go below the dimming mask.
            above_mask = []
            for child in self.children:
                if self.needs_full_redraw:
                    child.needs_full_redraw = self.needs_full_redraw
                if child.visible:
                    if child.is_above_mask:
                        above_mask.append(child)
                    else:
                        child.redraw()

            # Draw the dimming mask, if needed.
            if self.self_mask:
                self.do_mask()

            # Draw the widget's children who go above the dimming mask
            for child in above_mask:
                child.redraw()

        # Copy the entire image onto the widget's parent.
        if self.parent:
            self.parent.surface.blit(self.surface, self.real_pos)
        elif self.needs_redraw:
            pygame.display.flip()

        self.needs_redraw = False
        self.needs_full_redraw = False

    def add_handler(self, *args, **kwargs):
        """Handler pass-through."""
        if self.parent:
            self.parent.add_handler(*args, **kwargs)

    def remove_handler(self, *args, **kwargs):
        """Handler pass-through."""
        if self.parent:
            self.parent.remove_handler(*args, **kwargs)

    def add_key_handler(self, *args, **kwargs):
        """Handler pass-through."""
        if self.parent:
            self.parent.add_key_handler(*args, **kwargs)

    def remove_key_handler(self, *args, **kwargs):
        """Handler pass-through."""
        if self.parent:
            self.parent.remove_key_handler(*args, **kwargs)

    def add_focus_widget(self, *args, **kwargs):
        """Focus pass-through."""
        if self.parent:
            self.parent.add_focus_widget(*args, **kwargs)

    def remove_focus_widget(self, *args, **kwargs):
        """Focus pass-through."""
        if self.parent:
            self.parent.remove_focus_widget(*args, **kwargs)

    def took_focus(self, *args, **kwargs):
        """Focus pass-through."""
        if self.parent:
            self.parent.took_focus(*args, **kwargs)


class BorderedWidget(Widget):
    borders = causes_rebuild("_borders")
    border_color = causes_rebuild("_border_color")
    background_color = causes_rebuild("_background_color")

    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        self.borders = kwargs.pop("borders", ())
        self.border_color = kwargs.pop("border_color", g.colors["white"])
        self.background_color = kwargs.pop("background_color", g.colors["blue"])

        super(BorderedWidget, self).__init__(parent, *args, **kwargs)

    def rebuild(self):
        super(BorderedWidget, self).rebuild()

        # Fill the background.
        self.internal_surface.fill( self.background_color )

        # Draw borders
        my_size = self.real_size
        horiz = (my_size[0], 1)
        vert = (1, my_size[0])

        for edge in self.borders:
            if edge == constants.TOP:
                self.internal_surface.fill( self.border_color,
                                            (0, 0, my_size[0], 1) )
            elif edge == constants.LEFT:
                self.internal_surface.fill( self.border_color,
                                            (0, 0, 1, my_size[1]) )
            elif edge == constants.RIGHT:
                self.internal_surface.fill( self.border_color, 
                                            (my_size[0]-1, 0) + my_size )
            elif edge == constants.BOTTOM:
                self.internal_surface.fill( self.border_color, 
                                            (0, my_size[1]-1) + my_size )


class FocusWidget(Widget):
    has_focus = causes_rebuild("_has_focus")
    def __init__(self, *args, **kwargs):
        super(FocusWidget, self).__init__(*args, **kwargs)
        self.has_focus = True
        self.took_focus(self)

    def add_hooks(self):
        super(FocusWidget, self).add_hooks()
        self.parent.add_focus_widget(self)

    def remove_hooks(self):
        super(FocusWidget, self).remove_hooks()
        self.parent.remove_focus_widget(self)
