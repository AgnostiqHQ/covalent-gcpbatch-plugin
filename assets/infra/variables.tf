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
  description = "Path to the build context. Defaults to the root directory up two levels"
  default = "../.."
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
