import { SimpleGrid, Notification, Card, Text, Group, Image, Title } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { usePoll } from '@inertiajs/react';
import { ItemType, ContractType, ItemStatus } from '../types';


function Item({item}: {item: ItemType}) {
  return (
    <Group gap="xs">
      <Image w={30} src={"https://images.evetech.net/types/" + item.item_type.id + "/icon"} />
      <Text>
        {item.item_type.name} : {item.quantity.toLocaleString()}
      </Text>
    </Group>
  );
}

export function Contract({contract}: {contract: ContractType}) {
  if (contract.items === undefined) {
    console.error(`Bad contract: ${JSON.stringify(contract)}`)
    return <>Buggy contract</>
  }
  const to_give = contract.items.filter((item: ItemType) => item.status == ItemStatus.REQUESTED);
  const to_get = contract.items.filter((item: ItemType) => item.status == ItemStatus.OFFERED);

  const given_items = to_give.map((item: ItemType) => (<Item key={item.item_type.id} item={item} />));
  const received_items = to_get.map((item: ItemType) => (<Item key={item.item_type.id} item={item} />));


  const wordStart = / ./g;

  return (
    <Card radius='lg'>
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
        {contract.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ISK
      </Group>}

      {contract.reward > 0.0 &&
      <Group gap="xs">
        <Title order={6}>Reward:</Title>
        {contract.reward.toLocaleString()} ISK
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

    </Card>
  );
}

function Contracts({contracts}: {contracts: Array<ContractType>}) {
  usePoll(10000, {}, {keepAlive: true});

  if (contracts.length == 0) {
    return (
      <Notification title="No contracts found" color="red" icon={<IconX />} withCloseButton={false}/>
    );
  }

  console.log(`${contracts.length} contracts to display`);

  const contract_components = contracts.map((contract) => {
    return (
      <Contract key={contract.id} contract={contract} />
    );
  });
    

  return (
    <SimpleGrid m={20} cols={4}>
      {contract_components}
    </SimpleGrid>
  );
}

export default Contracts;