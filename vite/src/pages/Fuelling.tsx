import { Card, Chip, Flex, Group, Image, Loader, NativeSelect, Notification, SimpleGrid, Skeleton, Tabs, Text, Title } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';
import { useState } from 'react';
import useSWR from 'swr';
import { ContractType, LocationType } from '../types.tsx';
import { Contract, filterNames } from './Contracts.tsx';

const fetcher = (url: string | URL) => fetch(url).then((res) => res.json());

function Location({data}: {data: LocationType}) {

  const items = data.items.map((item) => {
    return (
      <Group key={item.item_type.id}><Image w={30} src={"https://images.evetech.net/types/" + item.item_type.id + "/icon"} /> {item.item_type.name}: {item.quantity.toLocaleString()}</Group>);
  });


  return (
    <Card radius="lg">
      <Card.Section pt={10} withBorder inheritPadding>
        <Title order={4} ta="center">{data.structure.name}</Title>
      </Card.Section>
      <Card.Section pt={10} pb={10} inheritPadding>
        {items.length > 0 && items || 
        <Text ta="center" c="green">No contracts at this location</Text>}
      </Card.Section>
    </Card>);
}

function Filtering({filter, setFilter, data}: {filter: any, setFilter: any, data: string[]}) {
  return (
    <NativeSelect value={filter} onChange={(event) => setFilter(event.currentTarget.value)}
      data={data}
      label="Filter by contract location"
     />
  );
}

function ErrorFiltering({filter, setFilter, errors, warnings}: {filter: any, setFilter: any, errors: string[], warnings: string[]}) {

  let error_chips = errors.map((error) => (
    <Chip color='red' key={error} value={error}>{filterNames.get(error)}</Chip>
  ));

  let warning_chips = warnings.map((warning) => (
    <Chip color='yellow' key={warning} value={warning}>{filterNames.get(warning)}</Chip>
  ));

  return (
    <Chip.Group multiple value={filter} onChange={setFilter}>
      <Group mt={23} pl={5}>
        <Chip value="normal">Normal Contracts</Chip>
        {error_chips}
        {warning_chips}
      </Group>
    </Chip.Group>
  );
}

const ALL_LOCATIONS: string = "All Locations"

function AllFuelContracts() {
  const { data, isLoading }: {data: ContractType[], isLoading: boolean} = useSWR("/fuel/all", fetcher, {refreshInterval: 5000});
  const [location_filter, set_location_filter] = useState(ALL_LOCATIONS);
  const [error_filter, set_error_filter] = useState(["normal", ...filterNames.keys() ]);
  let location_data: string[] = [];
  let contract_elements: JSX.Element | JSX.Element[] = <></>;

  let errors: string[] = [];
  let warnings: string[] = [];

  if (!isLoading)
  {
    let filtered = data;

    errors = [...new Set(data.flatMap((contract) => contract.errors))];
    warnings = [...new Set(data.flatMap((contract) => contract.warnings))];

    const locations = new Set(data.map((contract) => contract.location.name));
    location_data = Array.from(locations);
    location_data.unshift(ALL_LOCATIONS)

    if (location_filter !== ALL_LOCATIONS)
    {
      filtered = data.filter(x => x.location.name === location_filter);
    }


    filtered = filtered.filter(x => x.errors.some(y => error_filter.includes(y)) || x.errors.length == 0);
    filtered = filtered.filter(x => x.warnings.some(y => error_filter.includes(y)) || x.warnings.length == 0);
    if (!error_filter.includes("normal"))
    {
      filtered = filtered.filter(x => (x.errors.length > 0 || x.warnings.length > 0))
    }

    contract_elements = filtered.map((data: ContractType) => (
      <Contract key={data.id} contract={data} />
    ));
  }


  return (
    <>
    {isLoading && <Loader />}
    <Skeleton visible={isLoading} height={400}>
      <Flex align={"center"} pl={10}>
        {!isLoading && <Filtering data={location_data}  filter={location_filter} setFilter={set_location_filter} />}
        <ErrorFiltering filter={error_filter} setFilter={set_error_filter} errors={errors} warnings={warnings} />
      </Flex>
      <Group justify='flex-start' pl={10}><Text size="xs">Double-click a contract to open it on your logged in user</Text></Group>
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
        <Tabs.Tab value="location">By Fuelling Location</Tabs.Tab>
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