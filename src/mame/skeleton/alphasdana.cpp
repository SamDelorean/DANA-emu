// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
#include "cpu/m68000/m68000.h"

namespace {

class alphasdana_state : public driver_device
{
public:
	alphasdana_state(const machine_config &mconfig, device_type type, const char *tag)
		: driver_device(mconfig, type, tag)
		, m_maincpu(*this, "maincpu")
	{
	}

	void alphasdana(machine_config &config);

private:
	void program_map(address_map &map) ATTR_COLD;

	required_device<m68000_device> m_maincpu;
};

void alphasdana_state::program_map(address_map &map)
{
	// Synthetic post-bootstrap RAM profile, not physical Dana reset decoding.
	map(0x00000000, 0x003fffff).ram().share("ram");
}

void alphasdana_state::alphasdana(machine_config &config)
{
	// Placeholder CPU and clock; this does not model the DragonBall VZ.
	M68000(config, m_maincpu, 1'000'000);
	m_maincpu->set_addrmap(AS_PROGRAM, &alphasdana_state::program_map);
}

static INPUT_PORTS_START(alphasdana)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
	"AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
