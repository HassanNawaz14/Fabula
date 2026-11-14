import pygame
from pathlib import Path
from fabula.simulation.loader import LoadedBundle
from fabula.simulation import Session
from fabula.ui.app import FabulaApp
from fabula.training_data import generate_skeleton
from types import MappingProxyType

def run():
    # Create a quick skeleton bundle for testing UI immediately
    print("Generating skeleton bundle...")
    bundle = generate_skeleton("theft", seed=1, tone="cozy", difficulty="easy")
    
    # Wrap Bundle in LoadedBundle (stubbing root path for test)
    loaded = LoadedBundle(
        root=Path("."),
        world=bundle.world,
        clues=bundle.clues,
        npcs=MappingProxyType({npc.id: bundle.npcs[npc.id] for npc in bundle.world.npcs}),
        _truth=bundle.truth
    )
    session = Session(loaded)
    
    # Start the app
    print("Starting Fabula UI...")
    app = FabulaApp(session=session)
    app.run()

if __name__ == "__main__":
    run()
