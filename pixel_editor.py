import console, Image, numpy, photos, scene, ui, clipboard

class Pixel (scene.Rect):
	def __init__(self, x, y, w, h):
		scene.Rect.__init__(self, x, y, w, h)
		self.colors = [tuple((0, 0, 0, 0))]
		self.removed = False 
		
	def use(self):
		self.removed = False 
		
	def used(self):
		return len(self.colors) > 1 and not self.removed
		
	def undo(self):
		if self.removed:
			self.removed = False 
		elif self.used():
			self.colors.pop()
			
	def reset(self):
		self.colors = [tuple((0, 0, 0, 0))]

class PixelEditor(ui.View):
	def did_load(self):
		self.row = self.column = 16
		self.pixels = []
		self.pixel_path = []
		self.image_view = self.create_image_view()
		self.grid_layout = self.create_grid_layout()
		self.current_color = (1, 1, 1, 1)
		self.mode = 'pencil'

	def set_image(self, image=None):
		image = image or self.create_new_image()
		self.image_view.image = self.superview['preview'].image = image

	def create_grid_image(self):
		s = self.width/self.row if self.row > self.column else self.height/self.column
		path = ui.Path.rect(0, 0, *self.frame[2:])
		with ui.ImageContext(*self.frame[2:]) as ctx:
			ui.set_color((0, 0, 0, 0))
			path.fill()
			path.line_width = 2
			for y in xrange(self.column):
				for x in xrange(self.row):
					pixel = Pixel(x*s, y*s, s, s)
					path.append_path(ui.Path.rect(*pixel))
					self.pixels.append(pixel)
			ui.set_color('gray')
			path.stroke()
			return ctx.get_image()

	def create_grid_layout(self):
		image_view = ui.ImageView(frame=self.bounds)
		image_view.image = self.create_grid_image()
		self.add_subview(image_view)
		return image_view

	def create_image_view(self):
		image_view = ui.ImageView(frame=self.bounds)
		image_view.image = self.create_new_image()
		self.add_subview(image_view)
		return image_view

	def create_new_image(self):
		path = ui.Path.rect(*self.frame)
		with ui.ImageContext(self.width, self.width) as ctx:
			ui.set_color((0, 0, 0, 0))
			path.fill()
			return ctx.get_image()

	def create_image_from_history(self):
		path = ui.Path.rect(*self.frame)
		with ui.ImageContext(self.width, self.height) as ctx:
			for pixel in self.pixel_path:
				if pixel.removed:
					continue 
				ui.set_color(pixel.colors[-1])
				pixel_path = ui.Path.rect(*pixel)
				pixel_path.line_width = 0.5
				pixel_path.fill()
				pixel_path.stroke()
			img = ctx.get_image()
			return img
			
	def reset(self, row=None, column=None):
		self.row = row or self.row
		self.column = column or self.column
		self.pixels = []
		self.pixel_path = []
		self.grid_layout.image = self.create_grid_image()
		self.set_image()

	def undo(self):
		if not self.pixel_path:
			return
		pixel = self.pixel_path.pop()
		pixel.undo()
		self.set_image(self.create_image_from_history())

	def pencil(self, pixel):
		if pixel.colors[-1] != self.current_color or not pixel.used():
			pixel.use()
			pixel.colors.append(self.current_color)
			self.pixel_path.append(pixel)
			old_img = self.image_view.image
			path = ui.Path.rect(*pixel)
			with ui.ImageContext(self.width, self.height) as ctx:
				if old_img:
					old_img.draw()
				ui.set_color(self.current_color)
				pixel_path = ui.Path.rect(*pixel)
				pixel_path.line_width = 0.5
				pixel_path.fill()
				pixel_path.stroke()
				self.set_image(ctx.get_image())

	def eraser(self, pixel):
		if pixel.used() and not pixel.removed:
			pixel.removed = True 
			self.pixel_path.append(pixel)
		img = self.create_image_from_history()
		self.set_image(self.create_image_from_history())

	def color_picker(self, pixel):
		self.current_color = pixel.colors[-1]
		self.superview['colors'].set_color(pixel.colors[-1])

	def action(self, touch):
		p = scene.Point(*touch.location)
		for pixel in self.pixels:
			if p in pixel:
				eval('self.{}(pixel)'.format(self.mode))

	def touch_began(self, touch):
		self.action(touch)

	def touch_moved(self, touch):
		self.action(touch)

class ColorView (ui.View):
	def did_load(self):
		self.color = {'r':1, 'g':1, 'b':1, 'a':1}
		for subview in self.subviews:
			self.init_action(subview)

	def init_action(self, subview):
		if hasattr(subview, 'action'):
			subview.action = self.choose_color if subview.name != 'clear' else self.clear_user_palette
		if hasattr(subview, 'subviews'):
			for sv in subview.subviews:
				self.init_action(sv)

	def get_color(self):
		return tuple(self.color[i] for i in 'rgba')

	def set_color(self, color=None):
		color = color or self.get_color()
		for i, v in enumerate('rgba'):
			self[v].value = color[i]
			self.color[v] = color[i]
		self['current_color'].background_color = color
		self.superview['editor'].current_color = color

	def choose_color(self, sender):
		if sender.name in self.color:
			self.color[sender.name] = sender.value
			self.set_color()
		elif sender in self['palette'].subviews:
			if sender.background_color == (0, 0, 0, 0):
				sender.background_color = self.get_color()
			self.set_color(sender.background_color)
			color = {k:self.get_color()[i] for i, k in enumerate('rgba')}
			for i in 'rgba':
				self[i].value = color[i]
				
	def clear_user_palette(self, sender):
		for sv in self['palette'].subviews[10:]:
			sv.background_color = (0, 0, 0, 0)

class ToolbarView (ui.View):
	def did_load(self):
		for subview in self.subviews:
			self.init_actions(subview)

	def init_actions(self, subview):
		if hasattr(subview, 'action'):
			if isinstance(subview, ui.Button):
				subview.action = self.button_tapped
			elif isinstance(subview, ui.TextField):
				subview.action = self.textfield_action
		if hasattr(subview, 'subviews'):
			for sv in subview.subviews:
				self.init_actions(sv)

	def textfield_action(self, sender):
		if sender.name == 'bits':
			row, column = eval(sender.text)
			self.superview['editor'].reset(row, column)
			
	@ui.in_background
	def save_to_cameraroll(self, image):
		photos.save_image(image)
		console.hud_alert('Saved to Camera Roll')
		
	@ui.in_background
	def save_to_current_folder(self, image):
		with open(console.input_alert('File Name')+'.png', 'w+') as f:
			f.write(image.read())
		console.hud_alert('Saved to Current Folder')
			
	@ui.in_background
	def button_tapped(self, sender):
		pixel_editor = self.superview['editor']
		if sender.name == 'trash':
			msg = 'Are you sure you want to clear the pixel editor? Image will not be saved.'
			if console.alert('Trash', msg, 'Yes'):
				pixel_editor.image_view.image = pixel_editor.reset()
		elif sender.name == 'save':
			option = console.alert('Save Image', 'Saving options', 'Camera Roll', 'Clipboard')
			if option == 1:
				photos.save_image(pixel_editor.image_view.image)
				console.hud_alert('Saved to cameraroll')
			elif option == 2:
				clipboard.set_image(pixel_editor.image_view.image, format='png')
				console.hud_alert('Copied')
		elif sender.name == 'undo':
			pixel_editor.undo()
		elif sender.name == 'preview':
			v = ui.ImageView(frame=(0,0,512,512))
			v.image = pixel_editor.image_view.image
			v.present('sheet')
		else:
			pixel_editor.mode = sender.name
			for b in self['tools'].subviews:
				b.background_color = tuple((0, 0, 0, 0))
			sender.background_color = '#4C4C4C'

ui.load_view('pixel_editor').present()
