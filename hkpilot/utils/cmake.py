from hkpilot.utils import fancylogger
from hkpilot.utils.buildtools import BuildTools
from hkpilot.utils.files import mkdir, read_dependencies_file

import multiprocessing
import subprocess
import os

logger = fancylogger.getLogger(__name__)


class CMake(BuildTools):

    def __init__(self, path):
        super().__init__(path)
        self._type = "CMake"
        self._cmakelist_path = ""
        self._cmake_options = dict()  # dictionary containing cmake options

    def check_dependencies(self):
        self._depends_on.update(read_dependencies_file(os.path.join(self._path, self._cmakelist_path)))
        return True

    def configure(self):
        logger.info(f"Configuration of {self._package_name} in progress...")
        cmakelist_location = os.path.join(self._path, self._cmakelist_path)
        cmake_file = os.path.join(cmakelist_location, "CMakeLists.txt")
        if not os.path.exists(cmake_file):
            logger.error(f"Cannot find CMakeLists.txt in {cmakelist_location}")
            return False

        mkdir(self._build_folder)
        mkdir(self._install_folder)
        if "CMAKE_INSTALL_PREFIX" in self._cmake_options:
            logger.warn(f"CMAKE_INSTALL_PREFIX already defined as {self._cmake_options['CMAKE_INSTALL_PREFIX']}")
            logger.warn("Are you sure you know what you do?")
        else:
            self._cmake_options.update({"CMAKE_INSTALL_PREFIX": self._install_folder})
        cmake_cmd = f"cmake -S {cmakelist_location} -B {self._build_folder}"
        for key, value in self._cmake_options.items():
            cmake_cmd += f" -D{key}={value}"
        # if special dependencies, cmake could not find the XXXConfig.cmake file -> Add them manually by the command line
        for key, _ in self._depends_on.items():
            if key.lower() == "root":
                cmake_cmd += f" -D{key}_DIR={os.environ.get('HK_WORK_DIR')}/{key}/install-{os.environ.get('HK_SYSTEM')}/cmake"
            elif key.lower() == "geant4":
                cmake_cmd += f" -D{key}_DIR={os.environ.get('HK_WORK_DIR')}/{key}/install-{os.environ.get('HK_SYSTEM')}/lib64/cmake"
        logger.debug(f"Running <{cmake_cmd}>")
        try:
            ret_code = subprocess.check_call([cmake_cmd], stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Configuration of {self._package_name} failed!")
            return False
        if ret_code != 0:
            logger.error(f"Configuration of {self._package_name} failed!")
            return False
        logger.info(f"Configuration of {self._package_name} done successfully")
        return True

    def build(self):
        logger.info(f"Build of {self._package_name} in progress...")

        if self.n_procs == 0:
            self.n_procs = multiprocessing.cpu_count()
        cmake_cmd = f"cmake --build {self._build_folder} -j {self.n_procs}"
        logger.debug(f"Running <{cmake_cmd}>")
        ret_code = subprocess.check_call([cmake_cmd], stderr=subprocess.STDOUT, shell=True)
        if ret_code == 0:
            logger.info(f"Build of {self._package_name} done successfully")
            return True
        logger.error(f"Build of {self._package_name} failed!")
        return False

    def install(self):
        logger.info(f"Installation of {self._package_name} in progress...")

        cmake_cmd = f"cmake --build {self._build_folder} --target install -j {self.n_procs}"
        logger.debug(f"Running <{cmake_cmd}>")
        try:
            ret_code = subprocess.check_call([cmake_cmd], stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Installation of {self._package_name} failed!")
            return False
        if ret_code != 0:
            logger.error(f"Installation of {self._package_name} failed!")
            return False
        logger.info(f"Installation of {self._package_name} done successfully")
        return True
