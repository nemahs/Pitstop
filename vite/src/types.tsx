

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
export enum ValueTypes {
    NUMBER,
    LIST,
    STRING,
    NONE
}

export class FilterType {
    value: string;
    label: string;
    type: ValueTypes;

    constructor(name: string, label: string, value_type: ValueTypes = ValueTypes.NONE) {
        this.value = name;
        this.label = label;
        this.type = value_type;
    }
}

export const FILTERS: FilterType[] = [
    new FilterType("fuelRounding", "Round fuel to the nearest ", ValueTypes.NUMBER),
    new FilterType("allianceCheck", "Contractor in given alliances", ValueTypes.LIST),
    new FilterType("fuelHigh", "Total fuel requested is less than", ValueTypes.NUMBER),
    new FilterType("strontHigh", "Total stront requested is less than", ValueTypes.NUMBER),
    new FilterType("infoPopulated", "Info is not empty"),
    new FilterType("validStation", "Contract in a valid fuelling station")
];

