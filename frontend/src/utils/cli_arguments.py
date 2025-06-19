from argparse import ArgumentParser, Namespace


class FrontendArgumentsParser:

    @staticmethod
    def parse_arguments() -> Namespace:
        parser:ArgumentParser = ArgumentParser(description='Streamlit based frontend displaying a process analyzer dashboard')
        parser.add_argument('--bootstrap-servers', default='localhost:29092', type=str)
        parser.add_argument('--graphviz-declare', default='/frontend/src', help='path inside the container where Graphviz PNGs live', type=str)
        parser.add_argument('--group-id', default='frontend', type=str)
        parser.add_argument('--input-topic', type=str, default='dashboard-result', help='Name of the input topic')
        args: Namespace = parser.parse_args()
        print('Command line arguments have been parsed successfully.')

        return args
