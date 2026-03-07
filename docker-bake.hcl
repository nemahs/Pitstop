target "frontend" {
  secret = [
    "id=.env,src=prod.env"
  ]
}