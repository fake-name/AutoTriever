
import os.path
import site
import sys

wd = os.path.abspath(os.getcwd())
relp = "./scheduled/NuUpdate"
module_path = os.path.join(wd, relp)
abs_module_path = os.path.abspath(module_path)
site.addsitedir(abs_module_path)

print("Appended module %s to path" % (abs_module_path, ))

print(sys.path)



import WebMirror.OutputFilters.util.MessageConstructors  as msgpackers
import WebMirror.OutputFilters.Nu.NUHomepageFilter   as NUHomepageFilter
import WebMirror.OutputFilters.Nu.NuSeriesPageFilter as NuSeriesPageFilter


