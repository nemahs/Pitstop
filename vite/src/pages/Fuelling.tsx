import { Card, Group, Image, Loader, Notification, SimpleGrid, Skeleton, Tabs, Title } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';
import useSWR from 'swr';
import { ContractType, LocationType } from '../types.tsx';
import { Contract } from './Contracts.tsx';

const fetcher = (url: string | URL) => fetch(url).then((res) => res.json());

function Location({data}: {data: LocationType}) {

  const items = data.items.map((item) => {
    return (
      <Group key={item.item_type.id}><Image w={30} src={"https://images.evetech.net/types/" + item.item_type.id + "/icon"} /> {item.item_type.name}: {item.quantity.toLocaleString()}</Group>);
  });


  return (
    <Card radius="lg">
      <Card.Section pt={10} withBorder inheritPadding>
        <Title order={4}>{data.structure.name}</Title>
      </Card.Section>
      <Card.Section pt={10} pb={10} inheritPadding>
        {items}
      </Card.Section>
    </Card>);
}


function AllFuelContracts() {
  const { data, isLoading } = useSWR("/fuel/all", fetcher, {refreshInterval: 5000});
  let contract_elements = <></>;
  if (!isLoading)
  {
    contract_elements = data.map((data: ContractType) => (
      <Contract key={data.id} contract={data} />
    ));
  }


  return (
    <>
    {isLoading && <Loader />}
    <Skeleton visible={isLoading} height={400}>
      {!isLoading && data.length == 0 &&
        <Notification color="teal" icon={<IconCheck size={20} />} title="No fuel contracts, good work!" withCloseButton={false} />
      }
      <SimpleGrid p={10} cols={4}>
        {contract_elements}
      </SimpleGrid>
    </Skeleton>
    </>
  );
}

function ByLocation() {
  const { data, isLoading } = useSWR("/fuel/by-location", fetcher, {refreshInterval: 5000});
  let location_elements = <></>;

  if (!isLoading && data !== undefined)
  {
    location_elements = data.map((location: LocationType) => (
      <Location key={location.structure.id} data={location} />));
  }

  return (
    <Skeleton visible={isLoading} height={400}>
      <SimpleGrid p={10} cols={3}>
        {location_elements}
      </SimpleGrid>
    </Skeleton>
  );

}

function Fuelling()
{
  return (
    <Tabs defaultValue="all" activateTabWithKeyboard={false}>
      <Tabs.List>
        <Tabs.Tab value="all">All Fuel Contracts</Tabs.Tab>
        <Tabs.Tab value="location">By Contract Location</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="all">
          <AllFuelContracts />
      </Tabs.Panel>
      <Tabs.Panel value="location">
        <ByLocation />
      </Tabs.Panel>
    </Tabs>);
}

export default Fuelling;