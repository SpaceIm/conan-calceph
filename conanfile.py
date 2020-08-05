import glob
import os

from conans import ConanFile, AutoToolsBuildEnvironment, VisualStudioBuildEnvironment, tools

class CalcephConan(ConanFile):
    name = "calceph"
    description = "CALCEPH is designed to access the binary planetary ephemeris " \
                  "files, such INPOPxx, JPL DExxx and SPICE ephemeris files."
    license = ["CECILL-C", "CECILL-B", "CECILL-2.1"]
    topics = ("conan", "calceph", "ephemeris", "astronomy")
    homepage = "https://www.imcce.fr/inpop/calceph"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threadsafe": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threadsafe": False
    }

    _autotools= None

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.cppstd
        del self.settings.compiler.libcxx
        if self.settings.compiler == "Visual Studio":
            del self.options.threadsafe

    def build_requirements(self):
        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio" and \
           "CONAN_BASH_PATH" not in os.environ and tools.os_info.detect_windows_subsystem() != "msys2":
            self.build_requires("msys2/20190524")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename(self.name + "-" + self.version, self._source_subfolder)

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        if self.settings.compiler == "Visual Studio":
            self._build_msvc()
        else:
            autotools = self._configure_autotools()
            autotools.make()

    def _build_msvc(self):
        with tools.chdir(self._source_subfolder):
            with tools.vcvars(self.settings):
                with tools.environment_append(VisualStudioBuildEnvironment(self).vars):
                    self.run("nmake -f Makefile.vc")

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        args = []
        args.append("--disable-static" if self.options.shared else "--enable-static")
        args.append("--enable-shared" if self.options.shared else "--disable-shared")
        args.append("--enable-thread" if self.options.threadsafe else "--disable-thread")
        args.extend([
            "--disable-fortran",
            "--disable-python",
            "--disable-python-package-system",
            "--disable-python-package-user",
            "--disable-mex-octave"
        ])
        self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        self._autotools.configure(args=args, configure_dir=self._source_subfolder)
        return self._autotools

    def package(self):
        self.copy("COPYING", dst="licenses", src=self._source_subfolder)
        if self.settings.compiler == "Visual Studio":
            self.run("nmake -f Makefile.vc install")
        else:
            autotools = self._configure_autotools()
            autotools.install()
            tools.rmdir(os.path.join(self.package_folder, "libexec"))
            tools.rmdir(os.path.join(self.package_folder, "share"))
            for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
                os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bin_path))
        self.env_info.PATH.append(bin_path)
