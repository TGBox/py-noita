"""Sample Community Mod demonstrating Py-Noita Modding API."""

from py_noita.system.mod_api import ModAPI
from py_noita.weapons.gene import Gene, GeneType
from py_noita.entities.enemy import Enemy
from py_noita.ui.codex import Strain
from py_noita.simulation.materials import STATE_LIQUID


class TumorCarrier(Enemy):
    """Custom community enemy that wanders and leaves necrotic slime."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, enemy_type="TUMOR_CARRIER", hp=45.0, width=16, height=16, blood_mat=45)
        self.name = "Tumor-Träger"


def init(api: ModAPI):
    """Entry point called when mod is loaded."""
    # 1. Custom Material: Nekro-Schleim (ID 45)
    api.register_material(
        mat_id=45,
        name="Nekro-Schleim",
        state=STATE_LIQUID,
        density=1.3,
        colors=[(90, 20, 110), (120, 30, 140), (70, 10, 90)],
        flammability=15,
        dispersion=2,
        glow=180,
    )

    # 2. Custom Gene: Nekro-Tentakel
    necro_gene = Gene(
        id="NECRO_TENTACLE",
        name="Nekro-Tentakel",
        gene_type=GeneType.PROJECTILE,
        description="Feuert ein peitschendes nekrotisches Tentakel-Geschoss.",
        biomass_cost=18.0,
        damage=22.0,
        speed=6.0,
    )
    api.register_gene(necro_gene)

    # 3. Custom Enemy: Tumor-Träger
    api.register_enemy("TUMOR_CARRIER", lambda x, y: TumorCarrier(x, y))

    # 4. Custom Strain: Nekrotischer Symbiot
    necro_strain = Strain(
        strain_id="STRAIN_NECROMANCER",
        name="Nekrotischer Symbiot",
        description="Ein finsterer Wirt, der nekrotische Sporen und Tentakel abfeuert.",
        unlock_cost=100,
        starter_gene_ids=["NECRO_TENTACLE"],
        starter_gland_mat=45,
    )
    api.register_strain(necro_strain)

    # 5. Lifecycle Hooks
    @api.hook("on_run_start")
    def on_run_start(game):
        pass
