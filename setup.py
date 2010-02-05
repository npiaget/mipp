from distutils.core import setup, Extension

ext = Extension('xrit/_convert', ['xrit/convert/wrap_convert.c',\
                                 'xrit/convert/10216.c'],\
                extra_compile_args = ['-std=c99', '-O9'])


setup(name = 'xrit',
      version = '0.1',
      package_dir = {'xrit': 'xrit'},
      packages = ['xrit'],
      ext_modules = [ext,]
      )