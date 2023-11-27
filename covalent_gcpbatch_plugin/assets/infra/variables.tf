# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the Apache License 2.0 (the "License"). A copy of the
# License may be obtained with this software package or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Use of this file is prohibited except in compliance with the License.
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


variable "project_id" {
  type    = string
  default = "covalenttesting"
}

variable "access_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Google cloud access token for authenticating to the artifact registry"
}

variable "context" {
  type        = string
  description = "Path to the build context. Defaults to the root directory up three levels"
  default     = "../../.."
}

variable "prerelease" {
  type        = string
  description = "Specify if the latest pre-release version of Covalent is to be installed when building the docker container"
  default     = ""
}

variable "covalent_package_version" {
  type        = string
  description = "Covalent version to be installed in the container"
  default     = "covalent"
}

variable "prefix" {
  type    = string
  default = "covalent"
}

variable "key_path"{
  type = string
  description = "JSON file containing the credentials to connect to google provider"
  default = ""
}
