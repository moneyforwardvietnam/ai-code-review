module "vpc" {
  source     = "./modules/vpc"
  name       = local.cluster_name
  tags       = merge({ env = local.env }, module.eks.tags.shared)
  cidr       = local.vpc_cidr
  enable_igw = true
  enable_ngw = true
  single_ngw = true
}

module "eks" {
  source                    = "./modules/eks"
  name                      = local.cluster_name
  tags                      = { env = local.env }
  subnets                   = values(module.vpc.subnets["private"])
  enabled_cluster_log_types = local.cluster_log_types
  kubernetes_version        = local.kubernetes_version
  managed_node_groups       = local.managed_node_groups
  fargate_profiles          = []
}


module "rancher_server" {
  source = "./modules/rancher-server"

  env                  = local.env
  cluster_name         = module.eks.cluster.name
  oidc                 = module.eks.oidc
  aws_region           = local.aws_region
  aws_access_key       = var.aws_access_key
  aws_secret_key       = var.aws_secret_key
  rancher_version      = local.rancher_version
  cert_manager_version = local.cert_manager_version
  rancher_domain       = local.domain
  zone_id              = local.zone_id
  admin_password       = var.rancher_server_admin_password
  kubeconfig           = module.eks.kubeconfig
}

module "cluster-autoscaler" {
  source       = "./modules/cluster-autoscaler"
  cluster_name = module.eks.cluster.name
  oidc         = module.eks.oidc
  tags         = { env = local.env }
}

module "container-insights" {
  source       = "./modules/container-insights"
  cluster_name = module.eks.cluster.name
  oidc         = module.eks.oidc
  tags         = { env = local.env }
  features = {
    enable_metrics = true
    enable_logs    = true
  }
}

module "metrics-server" {
  source       = "./modules/metrics-server"
  cluster_name = module.eks.cluster.name
  oidc         = module.eks.oidc
  tags         = { env = local.env }
  helm = {
    version = "3.8.2"
    vars    = {}
  }
}

module "prometheus" {
  source       = "./modules/prometheus"
  cluster_name = module.eks.cluster.name
  oidc         = module.eks.oidc
  tags         = { env = local.env }
  helm = {
    version = "15.9.0"
    vars = {
      "alertmanager.persistentVolume.storageClass" = "gp2"
      "server.persistentVolume.storageClass"       = "gp2"
    }
  }
}
