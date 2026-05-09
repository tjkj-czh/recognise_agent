export interface User {
  id: number
  username: string
  real_name: string
  role_name: string
}

export interface LandSupply {
  id: number
  resource_id: string
  transfer_no: string
  district: string
  land_use_type: string
  area_sqm: number
  area_mu: number
  plot_ratio: number | null
  starting_price: number | null
  transaction_price: number | null
  transaction_date: string | null
  estimated_date: string | null
  transaction_stage: string
  system_type: string
  longitude: number
  latitude: number
  plot_name: string
  created_at: string
}
