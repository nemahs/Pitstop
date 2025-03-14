import { router } from '@inertiajs/core';
import { usePoll } from '@inertiajs/react';
import { Badge, Card, Group, Image, List, ListItem, Notification, NumberFormatter, SimpleGrid, Text, Title } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { ContractType, ItemStatus, ItemType } from '../types';


function Item({item}: {item: ItemType}) {
  return (
    <Group gap="xs">
      <Image w={30} src={"https://images.evetech.net/types/" + item.item_type.id + "/icon"} />
      <Text>
        {item.item_type.name} : <NumberFormatter thousandSeparator value={item.quantity} />
      </Text>
    </Group>
  );
}

const filterNames: Record<string, string> = {
  "fuelRounding": "Fuel not rounded correctly",
  "fuelHigh": "Fuel amounts too high",
  "strontHigh": "Stront amounts too high",
  "allianceCheck": "Contractor not in the correct alliance",
  "infoPopulated": "No description given"
}

export function Contract({contract, disableFilters = false}: {contract: ContractType, disableFilters?: boolean}) {
  if (contract.items === undefined) {
    console.error(`Bad contract: ${JSON.stringify(contract)}`)
    return <>Buggy contract</>
  }
  const to_give = contract.items.filter((item: ItemType) => item.status == ItemStatus.REQUESTED);
  const to_get = contract.items.filter((item: ItemType) => item.status == ItemStatus.OFFERED);

  const given_items = to_give.map((item: ItemType) => (<Item key={item.item_type.id} item={item} />));
  const received_items = to_get.map((item: ItemType) => (<Item key={item.item_type.id} item={item} />));


  const errors = contract.errors.map((error: string, i) => (<ListItem key={i}>{filterNames[error]}</ListItem>));
  const warnings = contract.warnings.map((warning: string, i) => (<ListItem key={i}>{filterNames[warning]}</ListItem>));

  const wordStart = / ./g;

  return (
    <Card styles={{root: {cursor: 'pointer'}}} radius='lg' onDoubleClick={() => router.post("/contracts/open", {'id': contract.id})}>
      <Group gap="xs">
        <Title order={6}>From:</Title>
        {contract.creator.name}
        <Image w={30} src={"https://images.evetech.net/characters/" + contract.creator.id + "/portrait"} />
      </Group>

      <Group gap="xs" preventGrowOverflow wrap='nowrap'>
        <Title order={6}>Location:</Title>
        <Text truncate="end">{contract.location.name}</Text>
      </Group>
      <Group gap="xs">
        <Title order={6}>Type:</Title>
        {contract.type.replaceAll("_", " ").replace(/^./, (char: string) => char.toUpperCase()).replaceAll(wordStart, (char: string) => char.toUpperCase())}
      </Group>

      <Group gap="xs">
        <Title order={6}>Description:</Title>
        {contract.description != "" ? `"${contract.description}"` : "No Description" }
      </Group>

      {contract.price > 0.0 &&
      <Group gap="xs">
        <Title order={6}>Price:</Title>
        <NumberFormatter value={contract.price} thousandSeparator decimalScale={2} suffix=' ISK' />
      </Group>}

      {contract.reward > 0.0 &&
      <Group gap="xs">
        <Title order={6}>Reward:</Title>
        <NumberFormatter value={contract.reward} thousandSeparator decimalScale={2} suffix=' ISK' />
      </Group>}

      {given_items.length > 0 &&
      <Card.Section withBorder inheritPadding pt={10} pb={10}>
        <Title order={6} pb={5}>Asking for</Title>
        {given_items}
      </Card.Section>}

      {received_items.length > 0 &&
      <Card.Section withBorder inheritPadding pt={10} pb={10}>
        <Title order={6} pb={5}>Offering</Title>
        {received_items}
      </Card.Section>}


      {given_items.length == 0 && received_items.length == 0 && 
      <Card.Section withBorder inheritPadding pt={10} pb={10}>
        <Title order={6} pb={5}>No items found</Title>
      </Card.Section>}
      
      { !disableFilters && (errors.length > 0 || warnings.length > 0) &&
      <Card.Section inheritPadding pb={5}>
        {errors.length > 0 &&
          <>
          <Title order={6}>Errors</Title>
          <List>{errors}</List>
         </>
         }
        {warnings.length > 0 && 
        <>
          <Title order={6}>Warnings</Title>
          <List>{warnings}</List>
        </>
        }

      </Card.Section>}


      { !disableFilters && (errors.length > 0 || warnings.length > 0) &&
        <Group justify='flex-end'>
          { errors.length > 0 && 
            <Badge autoContrast color='red'>Reject Contract</Badge>
          }

          { errors.length == 0 && warnings.length > 0 &&
            <Badge autoContrast color='yellow'>Leave for leadership</Badge>
          }
        </Group>
      }
    </Card>
  );
}

function Contracts({contracts}: {contracts: Array<ContractType>}) {
  usePoll(5000, {}, {keepAlive: true});

  if (contracts.length == 0) {
    return (
      <Notification title="No contracts found" color="red" icon={<IconX />} withCloseButton={false}/>
    );
  }

  console.debug(`${contracts.length} contracts to display`);

  const contract_components = contracts.map((contract) => {
    return (
      <Contract key={contract.id} contract={contract} disableFilters />
    );
  });
    

  return (
    <SimpleGrid m={20} cols={4}>
      {contract_components}
    </SimpleGrid>
  );
}

export default Contracts;