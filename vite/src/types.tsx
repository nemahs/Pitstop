

export interface NamedItem {
  name: string;
  id: number;
}

export enum ItemStatus {
  OFFERED = "offered",
  REQUESTED = "requested",
}

export interface ItemType {
  item_type: NamedItem;
  quantity: number;
  status: ItemStatus;
}

export interface ContractType {
  id: number;
  type: string;
  creator: NamedItem;
  location: NamedItem;
  price: number;
  reward: number;
  description: string;
  items: Array<ItemType>;
  errors: Array<string>;
  warnings: Array<string>;
}

export interface LocationType {
  structure: NamedItem;
  items: Array<ItemType>;
}