import { Tabs } from "@mantine/core";
import { FilterManagement, SavedFilter } from "../admin_components/ContractFilters";
import { StationManagement } from "../admin_components/Stations";


function Admin({filters}: {filters: SavedFilter[]}) {
    return (
        <Tabs defaultValue="filter" activateTabWithKeyboard={false}>
            <Tabs.List>
                <Tabs.Tab value="users">User Management</Tabs.Tab>
                <Tabs.Tab value="filter">Contract Filters</Tabs.Tab>
                <Tabs.Tab value="stations">Fuelling Stations</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="users">
                Add shit here
            </Tabs.Panel>

            <Tabs.Panel value="stations">
                <StationManagement />
            </Tabs.Panel>

            <Tabs.Panel value="filter">
                <FilterManagement filters={filters} />
            </Tabs.Panel>
        </Tabs>
    );
}

export default Admin;