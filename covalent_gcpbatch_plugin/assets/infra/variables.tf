# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the GNU Affero General Public License 3.0 (the "License").
# A copy of the License may be obtained with this software package or at
#
#      https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Use of this file is prohibited except in compliance with the License. Any
# modifications or derivative works of this file must retain this copyright
# notice, and modified files must contain a notice indicating that they have
# been altered from the originals.
#
# Covalent is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the License for more details.
#
# Relief from the License may be granted by purchasing a commercial license.


variable project_id {
  type    = string
  default = "aq-gcp-batch-test-10011"
}

variable access_token {
  type = string
  default = ""
  sensitive = true
  description = "Google cloud access token for authenticating to the artifact registry"
}

variable context {
  type = string
  description = "Path to the build context. Defaults to the root directory up three levels"
  default = "../../.."
}

variable prerelease {
  type = string
  description = "Specify if the latest pre-release version of Covalent is to be installed when building the docker container"
  default = ""
}

variable covalent_package_version {
  type = string
  description = "Covalent version to be installed in the container"
  default = "covalent"
}

variable prefix {
  type = string
  default = "venkat"
}
