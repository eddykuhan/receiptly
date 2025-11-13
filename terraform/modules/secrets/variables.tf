variable "secrets" {
  description = "Map of secret names to their values"
  type = map(object({
    description = string
    value       = string
  }))
}

variable "recovery_window_days" {
  description = "Number of days to retain secret after deletion"
  type        = number
  default     = 7
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
